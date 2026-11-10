SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS meta DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
GRANT ALL PRIVILEGES ON meta.* TO 'datapilot'@'%';

USE meta;

DROP TABLE IF EXISTS table_info;
CREATE TABLE table_info
(
    id          VARCHAR(64) PRIMARY KEY COMMENT 'Table ID',
    name        VARCHAR(128) COMMENT 'Table name',
    role        VARCHAR(32) COMMENT 'Table role (fact/dim)',
    description TEXT COMMENT 'Table description'
);

DROP TABLE IF EXISTS column_info;
CREATE TABLE column_info
(
    id          VARCHAR(64) PRIMARY KEY COMMENT 'Column ID',
    name        VARCHAR(128) COMMENT 'Column name',
    type        VARCHAR(64) COMMENT 'Data type',
    role        VARCHAR(32) COMMENT 'Column role (primary_key,foreign_key,measure,dimension)',
    examples    JSON COMMENT 'Sample values',
    description TEXT COMMENT 'Column description',
    alias       JSON COMMENT 'Column aliases',
    table_id    VARCHAR(64) COMMENT 'Parent table ID'
);

DROP TABLE IF EXISTS metric_info;
CREATE TABLE metric_info
(
    id               VARCHAR(64) PRIMARY KEY COMMENT 'Metric ID',
    name             VARCHAR(128) COMMENT 'Metric name',
    description      TEXT COMMENT 'Metric description',
    relevant_columns JSON COMMENT 'Associated columns',
    alias            JSON COMMENT 'Metric aliases'
);

DROP TABLE IF EXISTS column_metric;
CREATE TABLE column_metric
(
    column_id VARCHAR(64) COMMENT 'Column ID',
    metric_id VARCHAR(64) COMMENT 'Metric ID',
    PRIMARY KEY (column_id, metric_id)
);
