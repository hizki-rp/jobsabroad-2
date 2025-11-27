-- SQL script to create email tables manually
-- Run this if migrations don't work

-- EmailTemplate table
CREATE TABLE IF NOT EXISTS emails_emailtemplate (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    subject VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- EmailLog table
CREATE TABLE IF NOT EXISTS emails_emaillog (
    id BIGSERIAL PRIMARY KEY,
    recipient_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    subject VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    template_id BIGINT REFERENCES emails_emailtemplate(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'bounced')),
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL
);

-- BulkEmail table
CREATE TABLE IF NOT EXISTS emails_bulkemail (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    template_id BIGINT REFERENCES emails_emailtemplate(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'sending', 'sent', 'failed')),
    total_recipients INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    created_by_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE
);

-- BulkEmail recipients many-to-many table
CREATE TABLE IF NOT EXISTS emails_bulkemail_recipients (
    id BIGSERIAL PRIMARY KEY,
    bulkemail_id BIGINT NOT NULL REFERENCES emails_bulkemail(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    UNIQUE(bulkemail_id, user_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS emails_emaillog_recipient_idx ON emails_emaillog(recipient_id);
CREATE INDEX IF NOT EXISTS emails_emaillog_status_idx ON emails_emaillog(status);
CREATE INDEX IF NOT EXISTS emails_emaillog_created_at_idx ON emails_emaillog(created_at);
CREATE INDEX IF NOT EXISTS emails_bulkemail_created_at_idx ON emails_bulkemail(created_at);
CREATE INDEX IF NOT EXISTS emails_bulkemail_status_idx ON emails_bulkemail(status);

-- Insert default templates
INSERT INTO emails_emailtemplate (name, subject, body, is_active) VALUES
('welcome', 'Welcome to Addis Temari!', 'Dear {{user_name}},

Welcome to Addis Temari! We''re excited to have you join our community of students pursuing their dreams.

Your account has been successfully created and you can now:
- Browse our extensive database of universities
- Track your application progress
- Access premium content and features

If you have any questions, feel free to contact our support team.

Best regards,
The Addis Temari Team', TRUE),

('subscription_reminder', 'Your Addis Temari subscription is expiring soon', 'Dear {{user_name}},

Your Addis Temari subscription will expire soon. To continue enjoying our premium features, please renew your subscription.

Premium features include:
- Access to detailed university information
- Application tracking tools
- Priority support

Renew now to avoid any interruption in service.

Best regards,
The Addis Temari Team', TRUE),

('application_deadline', 'Important: Application deadline approaching', 'Dear {{user_name}},

This is a friendly reminder that you have university applications with upcoming deadlines.

Please check your dashboard to review your applications and ensure all required documents are submitted on time.

Best regards,
The Addis Temari Team', TRUE)
ON CONFLICT (name) DO NOTHING;




