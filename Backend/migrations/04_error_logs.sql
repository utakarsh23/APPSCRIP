CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT now(),
    endpoint TEXT NOT NULL,
    http_method TEXT NOT NULL,
    error_message TEXT,
    stack_trace TEXT,
    ip_address TEXT,
    user_id UUID
);

CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs(user_id);
