export interface User {
  id: number;
  email: string;
  username: string;
  avatar_url: string | null;
  is_admin: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Movie {
  id: number;
  kinopoisk_id: number;
  title: string;
  short_description: string | null;
  description: string | null;
  poster_url: string | null;
  year: number | null;
  runtime: number | null;
  rating: number | null;
  rating_kinopoisk?: number | null;
  director?: string | null;
  genres: { genre: { id: number; name: string } }[] | { id: number; name: string }[];
  cached_at: string;
}

export interface MovieSearchResult {
  kinopoisk_id: number;
  title: string;
  year: number | null;
  poster_url: string | null;
  director?: string | null;
  rating_kinopoisk?: number | null;
}

export interface GameSession {
  id: number;
  host_user_id: number | null;
  invite_code: string;
  status: "CREATED" | "PLAYING" | "FINISHED" | "CANCELLED";
  winner_session_movie_id: number | null;
  winner_movie_id?: number | null;
  winner_user_id?: number | null;
  game_type?: string | null;
  winner_session_movie?: SessionMovie | null;
  started_at: string;
  finished_at: string | null;
  created_at: string;
}

export interface SessionParticipant {
  id: number;
  user_id: number | null;
  guest_id: string | null;
  session_id: number;
  display_name: string;
  is_host: boolean;
  selected_session_movie_id: number | null;
}

export interface SessionMovie {
  id: number;
  session_id: number;
  movie_id: number;
  proposed_by_participant_id: number;
  movie?: Movie | null;
}

export interface RoomState {
  host_user_id: string;
  participants: Record<
    string,
    { username: string; connected: boolean; is_guest: boolean }
  >;
  status: "waiting" | "playing" | "finished";
}

export interface WSMessage {
  type: string;
  payload?: unknown;
}

export interface FlappyPlayer {
  id: string;
  y: number;
  velocity: number;
  alive: boolean;
  score: number;
}

export interface FlappyPipe {
  x: number;
  gap_y: number;
  width: number;
  gap_height: number;
}

export interface FlappyState {
  type: "state";
  players: Record<string, FlappyPlayer>;
  pipes: FlappyPipe[];
  tick: number;
  running: boolean;
  // Bug 4 fix: server-driven phase state. `phase` tells the client
  // which overlay to render. `participants` / `confirmed_ids` /
  // `ready_ids` are used by the confirm-wait and ready-wait overlays.
  phase?: "confirm_wait" | "ready_wait" | "playing" | "game_over";
  participants?: string[];
  confirmed_ids?: string[];
  ready_ids?: string[];
}

export interface FlappyGameOver {
  type: "game_over";
  winner_id: string | null;
  scores: Record<string, number>;
}

export interface TournamentMovieCard {
  movie_id: number;
  kinopoisk_id: number;
  title: string;
  poster_url: string | null;
  year: number | null;
  rating: number | null;
}

export interface TournamentMatch {
  round_no: number;
  match_no: number;
  left: TournamentMovieCard;
  right: TournamentMovieCard;
}

export interface TournamentParticipant {
  id: number;
  user_key: string;
  display_name: string;
  is_host: boolean;
}

export interface TournamentRoomState {
  room_id: number;
  title: string;
  status: "LOBBY" | "RUNNING" | "FINISHED";
  bracket_size: number;
  round_name: string | null;
  progress: number;
  participants: TournamentParticipant[];
  current_match: TournamentMatch | null;
  winner: TournamentMovieCard | null;
}

export interface TournamentRoomCreated {
  room_id: number;
  user_key: string;
  room: TournamentRoomState;
}

export interface Genre {
  id: number;
  name: string;
}
