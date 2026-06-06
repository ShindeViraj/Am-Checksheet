-- TPM Checkpoint Reporting System - Database Setup
-- Run this script to initialize the partitioned database schema.

CREATE TABLE IF NOT EXISTS checkpoints (
    id BIGINT AUTO_INCREMENT,
    machine_id VARCHAR(50) NOT NULL,
    checkpoint_no INT NOT NULL,
    checkpoint_ok TINYINT(1) NOT NULL,
    checkpoint_not_ok TINYINT(1) NOT NULL,
    time_taken DECIMAL(10,3),
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id, start_time),
    UNIQUE KEY uq_checkpoint (machine_id, checkpoint_no, start_time, end_time),
    INDEX idx_machine(machine_id),
    INDEX idx_created(created_at),
    INDEX idx_machine_date(machine_id, created_at)
)
PARTITION BY RANGE (YEAR(start_time) * 100 + MONTH(start_time)) (
    PARTITION p202606 VALUES LESS THAN (202607),
    PARTITION p202607 VALUES LESS THAN (202608),
    PARTITION p202608 VALUES LESS THAN (202609),
    PARTITION p202609 VALUES LESS THAN (202610),
    PARTITION p202610 VALUES LESS THAN (202611),
    PARTITION p202611 VALUES LESS THAN (202612),
    PARTITION p202612 VALUES LESS THAN (202701),
    PARTITION p202701 VALUES LESS THAN (202702),
    PARTITION p_max VALUES LESS THAN MAXVALUE
);
