-- Migration 004: optional Telegram chat_id for alert delivery
ALTER TABLE alerts
  ADD COLUMN IF NOT EXISTS telegram_chat_id TEXT;
