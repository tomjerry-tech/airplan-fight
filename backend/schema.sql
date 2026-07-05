CREATE TABLE IF NOT EXISTS players (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(12) NOT NULL,
    token CHAR(64) NOT NULL,
    is_online TINYINT(1) NOT NULL DEFAULT 0,
    current_room_id VARCHAR(16) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_players_name (name),
    UNIQUE KEY uq_players_token (token),
    KEY idx_players_current_room_id (current_room_id),
    KEY idx_players_is_online (is_online)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scores (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    player_id BIGINT UNSIGNED NOT NULL,
    score INT UNSIGNED NOT NULL,
    mode VARCHAR(32) NOT NULL,
    room_id VARCHAR(16) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_scores_score (score),
    KEY idx_scores_player_id (player_id),
    KEY idx_scores_mode_score (mode, score),
    CONSTRAINT fk_scores_player
        FOREIGN KEY (player_id) REFERENCES players(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rooms_history (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    room_id VARCHAR(16) NOT NULL,
    player1_id BIGINT UNSIGNED NOT NULL,
    player2_id BIGINT UNSIGNED NULL,
    score INT UNSIGNED NOT NULL,
    duration_sec INT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_rooms_history_room_id (room_id),
    KEY idx_rooms_history_score (score),
    KEY idx_rooms_history_player1_id (player1_id),
    KEY idx_rooms_history_player2_id (player2_id),
    CONSTRAINT fk_rooms_history_player1
        FOREIGN KEY (player1_id) REFERENCES players(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rooms_history_player2
        FOREIGN KEY (player2_id) REFERENCES players(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
