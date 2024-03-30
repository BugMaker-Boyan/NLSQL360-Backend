from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `user` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(16) NOT NULL UNIQUE,
    `hashed_password` VARCHAR(512) NOT NULL,
    `email` VARCHAR(350) NOT NULL,
    `llm_api_config_baseurl` VARCHAR(512),
    `llm_api_config_key` VARCHAR(512),
    KEY `idx_user_usernam_9987ab` (`username`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
