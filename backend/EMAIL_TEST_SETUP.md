# Email Test Configuration

## Overview
All test and development emails are automatically redirected to: **navidkamal@iut-dhaka.edu**

This ensures you can safely test the SmartEngage email notifications without sending messages to real customers.

## Configuration

### Notification Service (`src/services/notification_service.py`)

The `EmailNotificationProvider` class has been configured with:

```python
# Test mode: Always send to navidkamal@iut-dhaka.edu
self.test_email_override = "navidkamal@iut-dhaka.edu"
self.test_mode = True  # Set to False in production
```

### How It Works

1. **Test Mode Active**: When `test_mode = True`, all emails are redirected
2. **Original Recipient Shown**: The email includes a yellow banner showing who the original recipient was
3. **Full Email Styling**: You'll see the actual email as customers would receive it
4. **Bengali Content**: Messages support Bengali text (UTF-8 encoding)

### Email Template

The emails include:
- **Header**: Gradient purple header with "ShoktiAI" branding
- **Test Notice**: Yellow banner showing original recipient (in test mode)
- **Message Content**: AI-generated personalized message
- **Footer**: Unsubscribe notice and copyright

## Testing

### Run Email Test

```powershell
cd backend
python test_email_notification.py
```

This will:
1. Load SMTP configuration from `.env`
2. Send a test email to `navidkamal@iut-dhaka.edu`
3. Include both Bengali and English sample text
4. Show the full HTML-styled email

### Expected Output

```
🧪 Testing Email Notification

SMTP Configuration:
  Host: smtp.gmail.com
  Port: 465
  Username: your-email@gmail.com
  From: your-email@gmail.com (ShoktiAI)
  Provider: email

📧 Sending test notification to: navidkamal@iut-dhaka.edu
   Subject: Test - ShoktiAI SmartEngage Reminder

✅ Email notification sent successfully!
   Check your inbox (and spam folder)
```

### Check Email

1. Go to https://mail.google.com
2. Login with: navidkamal@iut-dhaka.edu
3. Look for email from "ShoktiAI"
4. Check spam folder if not in inbox

## Email Content Example

```
আসসালামু আলাইকুম!

এটি ShoktiAI থেকে একটি পরীক্ষা বার্তা।

আপনার হোম ক্লিনিং সার্ভিসের জন্য সময় হয়ে গেছে! 
গত মাসে আপনি আমাদের সেবা নিয়েছিলেন এবং সন্তুষ্ট ছিলেন। 
আবার বুক করতে নিচের লিংকে ক্লিক করুন।

---

Hello!

This is a test message from ShoktiAI SmartEngage.

It's time for your home cleaning service! Last month you used 
our service and were satisfied. Click below to book again.

Thank you,
ShoktiAI Team 🎉
```

## Production Configuration

When deploying to production:

1. Open `src/services/notification_service.py`
2. Find the `EmailNotificationProvider.__init__` method
3. Change: `self.test_mode = True` → `self.test_mode = False`
4. Restart the application

```python
# Production mode: Send to actual customer emails
self.test_email_override = "navidkamal@iut-dhaka.edu"
self.test_mode = False  # ← Change this to False for production
```

## Integration Tests

All integration tests (`tests/integration/test_smartengage_flow.py`) will also redirect emails to your test account, so you can verify the full flow end-to-end.

## Logs

The service logs all email operations:

```
INFO: Email notification provider initialized in TEST MODE - all emails will be sent to navidkamal@iut-dhaka.edu
INFO: TEST MODE: Redirecting email from customer@example.com to navidkamal@iut-dhaka.edu
INFO: Email notification sent to navidkamal@iut-dhaka.edu
```

## SMTP Configuration (.env)

Make sure these are set in your `.env` file:

```bash
# Email Configuration (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password  # Not your regular password!
SMTP_FROM_EMAIL=your-gmail@gmail.com
SMTP_FROM_NAME=ShoktiAI
NOTIFICATION_PROVIDER=email
```

### Gmail App Password

If using Gmail:
1. Go to https://myaccount.google.com/apppasswords
2. Generate a new app password for "ShoktiAI"
3. Use that 16-character password (not your regular Gmail password)

## Troubleshooting

### Email Not Arriving

1. **Check SMTP credentials**: Verify `.env` file has correct settings
2. **Check spam folder**: Gmail may filter automated emails
3. **Run test script**: `python test_email_notification.py`
4. **Check logs**: Look for error messages in console output
5. **Verify Gmail settings**: Ensure "Less secure app access" is enabled (if needed)

### Email Formatting Issues

- **Bengali text not showing**: Check UTF-8 encoding in HTML template
- **Styling broken**: Verify HTML email client (Gmail supports most CSS)
- **Test banner not showing**: Confirm `test_mode = True` in code

## Next Steps

Once email is working:
- T033: Implement deep link generator
- T034: Build SmartEngage orchestrator (uses this email service)
- T035: Create internal API endpoints to trigger campaigns
