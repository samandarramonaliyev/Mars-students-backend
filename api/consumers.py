import asyncio
import logging
from datetime import timedelta

import chess
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from .models import ChessGame, CoinTransaction, CoinNotification
from .chess_logic import calculate_reward


ACTIVE_TIMER_TASKS = {}
logger = logging.getLogger(__name__)


class ChessConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for realtime chess games."""

    async def connect(self):
        try:
            self.game_id = int(self.scope['url_route']['kwargs']['game_id'])
        except (TypeError, ValueError):
            await self.accept()
            await self.send_json({'type': 'error', 'message': 'game_not_found'})
            await self.close(code=4404)
            logger.warning("WS connect rejected: invalid game id")
            return

        self.user = self.scope.get('user')
        await self.accept()

        if not self.user or not self.user.is_authenticated:
            await self.send_json({'type': 'error', 'message': 'auth_failed'})
            await self.close(code=4401)
            logger.warning("WS connect rejected: unauthenticated")
            return

        game = await get_game(self.game_id)
        if not game:
            await self.send_json({'type': 'error', 'message': 'game_not_found'})
            await self.close(code=4404)
            logger.warning("WS connect rejected: game not found (id=%s)", self.game_id)
            return

        if not await is_user_in_game(game, self.user):
            await self.send_json({'type': 'error', 'message': 'not_in_game'})
            await self.close(code=4403)
            logger.warning("WS connect rejected: user not in game (id=%s, user=%s)", self.game_id, self.user.id)
            return

        self.group_name = f"chess_{self.game_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.send_json({
            'type': 'game_state',
            **await build_game_state(game, self.user)
        })

        await self.start_timer_task()
        logger.info("WS connected: game=%s user=%s", self.game_id, self.user.id)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info("WS disconnected: game=%s code=%s", getattr(self, 'game_id', None), close_code)

    async def receive_json(self, content, **kwargs):
        message_type = content.get('type')
        if message_type == 'move':
            await self.handle_move(content)
        elif message_type == 'resign':
            await self.handle_resign()

    async def handle_move(self, content):
        game = await get_game(self.game_id)
        if not game or game.status != ChessGame.Status.IN_PROGRESS:
            return

        if not await is_user_turn(game, self.user):
            await self.send_json({'type': 'error', 'message': 'Сейчас не ваш ход'})
            return

        from_square = content.get('from')
        to_square = content.get('to')
        promotion = content.get('promotion', 'q')
        if not from_square or not to_square:
            await self.send_json({'type': 'error', 'message': 'Некорректный ход'})
            return

        updated = await apply_move(
            game,
            from_square,
            to_square,
            promotion
        )
        if not updated:
            await self.send_json({'type': 'error', 'message': 'Недопустимый ход'})
            return

        await self.channel_layer.group_send(self.group_name, {
            'type': 'broadcast_move',
            'payload': updated
        })

        if updated.get('game_over_payload'):
            await self.channel_layer.group_send(self.group_name, {
                'type': 'broadcast_game_over',
                'payload': updated['game_over_payload']
            })

        # Если это игра с ботом и ход бота
        if updated.get('next_is_bot'):
            bot_move_payload = await apply_bot_move(updated['game_id'])
            if bot_move_payload:
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'broadcast_move',
                    'payload': bot_move_payload
                })
                if bot_move_payload.get('game_over_payload'):
                    await self.channel_layer.group_send(self.group_name, {
                        'type': 'broadcast_game_over',
                        'payload': bot_move_payload['game_over_payload']
                    })

    async def handle_resign(self):
        game = await get_game(self.game_id)
        if not game or game.status != ChessGame.Status.IN_PROGRESS:
            return

        payload = await finish_game(game, loser=self.user, ended_reason='resign')
        await self.channel_layer.group_send(self.group_name, {
            'type': 'broadcast_game_over',
            'payload': payload
        })

    async def broadcast_move(self, event):
        await self.send_json(event['payload'])

    async def broadcast_game_over(self, event):
        await self.send_json(event['payload'])

    async def broadcast_timer(self, event):
        await self.send_json(event['payload'])

    async def start_timer_task(self):
        if self.game_id in ACTIVE_TIMER_TASKS:
            return

        async def timer_loop():
            while True:
                game = await get_game(self.game_id)
                if not game or game.status != ChessGame.Status.IN_PROGRESS:
                    break

                timer_state = await get_timer_state(game)
                if timer_state.get('timeout'):
                    payload = await finish_game(
                        game,
                        loser=timer_state.get('loser'),
                        ended_reason='timeout'
                    )
                    await self.channel_layer.group_send(self.group_name, {
                        'type': 'broadcast_game_over',
                        'payload': payload
                    })
                    break

                await self.channel_layer.group_send(self.group_name, {
                    'type': 'broadcast_timer',
                    'payload': {
                        'type': 'timer_update',
                        **timer_state['payload']
                    }
                })
                await asyncio.sleep(1)

            ACTIVE_TIMER_TASKS.pop(self.game_id, None)

        ACTIVE_TIMER_TASKS[self.game_id] = asyncio.create_task(timer_loop())


@database_sync_to_async
def get_game(game_id):
    try:
        return ChessGame.objects.select_related('player', 'opponent', 'white_player').get(pk=game_id)
    except ChessGame.DoesNotExist:
        return None


@database_sync_to_async
def is_user_in_game(game, user):
    return user == game.player or user == game.opponent


@database_sync_to_async
def is_user_turn(game, user):
    if game.white_player == user and game.current_turn == 'white':
        return True
    if game.white_player != user and game.current_turn == 'black':
        return True
    return False


@database_sync_to_async
def build_game_state(game, user):
    player_color = 'white' if game.white_player == user else 'black'
    return {
        'game_id': game.id,
        'fen': game.fen_position,
        'move_history': game.move_history or [],
        'white_time': game.white_time,
        'black_time': game.black_time,
        'current_turn': game.current_turn,
        'status': game.status,
        'result': game.result,
        'ended_reason': game.ended_reason,
        'winner_id': game.winner_id,
        'loser_id': game.loser_id,
        'player_color': player_color,
        'opponent_type': game.opponent_type,
        'last_move': game.last_move
    }


@database_sync_to_async
def apply_move(game, from_square, to_square, promotion):
    board = chess.Board(game.fen_position)

    elapsed = get_elapsed_seconds(game)
    if game.current_turn == 'white':
        game.white_time = max(0, game.white_time - elapsed)
    else:
        game.black_time = max(0, game.black_time - elapsed)

    uci = f"{from_square}{to_square}{promotion if promotion else ''}"
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return None

    if move not in board.legal_moves:
        return None

    san = board.san(move)
    board.push(move)

    game.fen_position = board.fen()
    game.last_move = uci
    history = game.move_history or []
    history.append(san)
    game.move_history = history
    game.current_turn = 'white' if board.turn == chess.WHITE else 'black'
    game.last_move_at = timezone.now()

    game_over_payload = None
    if board.is_checkmate():
        loser_color = 'white' if board.turn == chess.WHITE else 'black'
        winner_color = 'black' if loser_color == 'white' else 'white'
        winner = game.white_player if winner_color == 'white' else get_black_player(game)
        loser = game.white_player if loser_color == 'white' else get_black_player(game)
        game_over_payload = finish_game_sync(game, winner, loser, 'checkmate')
    elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        game_over_payload = finish_game_sync(game, None, None, 'draw')
    else:
        game.save()

    payload = {
        'type': 'move',
        'game_id': game.id,
        'fen': game.fen_position,
        'last_move': game.last_move,
        'move_history': game.move_history,
        'current_turn': game.current_turn,
        'white_time': game.white_time,
        'black_time': game.black_time,
        'status': game.status,
        'result': game.result,
        'ended_reason': game.ended_reason,
        'winner_id': game.winner_id,
        'loser_id': game.loser_id,
        'next_is_bot': game.opponent_type == ChessGame.OpponentType.BOT and game.current_turn == 'black',
        'game_over': bool(game_over_payload),
        'game_over_payload': game_over_payload
    }
    return payload


def get_elapsed_seconds(game):
    if not game.last_move_at:
        return 0
    delta = timezone.now() - game.last_move_at
    return int(delta.total_seconds())


def get_black_player(game):
    return game.player if game.white_player != game.player else game.opponent


@database_sync_to_async
def get_timer_state(game):
    elapsed = get_elapsed_seconds(game)
    white_time = game.white_time
    black_time = game.black_time

    timeout = False
    loser = None
    if game.current_turn == 'white':
        white_time = max(0, white_time - elapsed)
        if white_time <= 0:
            timeout = True
            loser = game.white_player
    else:
        black_time = max(0, black_time - elapsed)
        if black_time <= 0:
            timeout = True
            loser = get_black_player(game)

    return {
        'payload': {
            'game_id': game.id,
            'white_time': white_time,
            'black_time': black_time,
            'current_turn': game.current_turn,
            'timeout': timeout
        },
        'timeout': timeout,
        'loser': loser
    }


@database_sync_to_async
def finish_game(game, loser, ended_reason):
    return finish_game_sync(game, None, loser, ended_reason)


def finish_game_sync(game, winner, loser, ended_reason):
    if game.status != ChessGame.Status.IN_PROGRESS:
        return {
            'type': 'game_over',
            'game_id': game.id,
            'status': game.status,
            'ended_reason': game.ended_reason,
            'winner_id': game.winner_id,
            'loser_id': game.loser_id,
        }

    if ended_reason == 'checkmate':
        pass
    if ended_reason == 'timeout' and loser:
        winner = winner or (game.white_player if loser != game.white_player else get_black_player(game))
    if ended_reason == 'resign':
        winner = winner or (game.white_player if loser != game.white_player else get_black_player(game))
    if ended_reason == 'draw':
        winner = None
        loser = None

    game.status = ChessGame.Status.FINISHED
    game.ended_reason = ended_reason
    game.winner = winner
    game.loser = loser
    game.finished_at = timezone.now()

    if winner is None and loser is None:
        game.result = ChessGame.Result.DRAW
    else:
        game.result = ChessGame.Result.WIN if game.player == winner else ChessGame.Result.LOSE

    # Обновляем таймеры до 0 если таймаут
    if ended_reason == 'timeout' and loser:
        if loser == game.white_player:
            game.white_time = 0
        else:
            game.black_time = 0

    # Начисляем награды
    if ended_reason in ['checkmate', 'timeout', 'resign', 'draw']:
        award_chess_rewards(game, winner)

    game.save()
    return {
        'type': 'game_over',
        'game_id': game.id,
        'status': game.status,
        'ended_reason': game.ended_reason,
        'winner_id': game.winner_id,
        'loser_id': game.loser_id,
        'result': game.result
    }


def award_chess_rewards(game, winner):
    if game.opponent_type == ChessGame.OpponentType.BOT:
        if not winner and not game.loser:
            coins = calculate_reward('BOT', game.bot_level, 'DRAW')
            if coins > 0:
                add_coins(game.player, coins, f'Шахматы: Ничья против {game.get_opponent_display()}')
            return
        if not winner:
            return
        if winner == game.player:
            coins = calculate_reward('BOT', game.bot_level, 'WIN')
            if coins > 0:
                add_coins(game.player, coins, f'Шахматы: Победа против {game.get_opponent_display()}')
        return

    # PvP
    if not winner:
        coins = calculate_reward('STUDENT', None, 'DRAW')
        if coins > 0:
            add_coins(game.player, coins, 'Шахматы: Ничья')
            if game.opponent:
                add_coins(game.opponent, coins, 'Шахматы: Ничья')
        return

    coins = calculate_reward('STUDENT', None, 'WIN')
    if coins > 0 and winner:
        add_coins(winner, coins, 'Шахматы: Победа')


def add_coins(user, amount, reason):
    if amount <= 0:
        return
    user.balance += amount
    user.save()
    CoinTransaction.objects.create(
        user=user,
        amount=amount,
        reason=reason,
        source=CoinTransaction.Source.CHESS,
        balance_after=user.balance
    )
    CoinNotification.objects.create(
        student=user,
        amount=amount,
        reason=reason
    )


async def apply_bot_move(game_id):
    game = await get_game(game_id)
    if not game or game.status != ChessGame.Status.IN_PROGRESS:
        return None

    if game.current_turn != 'black':
        return None

    board = chess.Board(game.fen_position)
    move = await asyncio.to_thread(get_stockfish_move, board, game.bot_level)
    if not move:
        return None

    from_sq = chess.square_name(move.from_square)
    to_sq = chess.square_name(move.to_square)
    promotion = move.promotion
    promo = chess.piece_symbol(promotion) if promotion else ''
    return await apply_move(game, from_sq, to_sq, promo)


def get_stockfish_move(board, bot_level):
    import chess.engine
    depth = 8 if bot_level == 'hard' else 5 if bot_level == 'medium' else 2
    try:
        engine = chess.engine.SimpleEngine.popen_uci("stockfish")
        result = engine.play(board, chess.engine.Limit(depth=depth))
        engine.quit()
        return result.move
    except Exception:
        return None
