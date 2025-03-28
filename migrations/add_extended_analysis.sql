-- Добавление колонки extended_analysis в таблицу comparison_sessions
ALTER TABLE comparison_sessions ADD COLUMN IF NOT EXISTS extended_analysis JSON; 