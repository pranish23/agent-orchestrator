# Sample Queries & Expected Outputs

## Single Service Queries

### 1. Calendar Search

**Query:** "What's on my calendar next week?"

**Expected Output:**
```
Found **8** events for next week:

📅 **Team Standup** - Mon 9:00 AM (Slack Huddle)
📅 **Client Meeting - Acme Corp** - Mon 10:00 AM (Zoom)
📅 **Q4 Budget Review Meeting** - Mon 2:00 PM (Conference Room A)
📅 **Meeting with John** - Tue 3:00 PM (Office)
📅 **Meeting with John Miller** - Wed 10:00 AM (HR Office)
📅 **Sprint Planning** - Thu 2:00 PM (Conference Room B)
📅 **Dentist Appointment** - Fri 11:00 AM (Medical Center)
📅 **Istanbul → NYC Flight (TK1234)** - Sat 10:30 AM (Istanbul Airport)
```

---

### 2. Email Search by Sender

**Query:** "Find emails from sarah@company.com about the budget"

**Expected Output:**
```
Found **1** matching email:

📧 **Q4 Budget Review Meeting**
   From: sarah@company.com
   _Hi team, Please find attached the Q4 budget review documents..._
```

---

### 3. Drive File Search

**Query:** "Show me PDFs in Drive from last month"

**Expected Output:**
```
Found **2** file(s):

📄 **Q4 Budget Report.pdf**
   _Q4 2024 Budget Report - Revenue: $2.5M, Expenses: $1.8M..._

📄 **Project Timeline.pdf**
   _Project Widget X Timeline - Phase 1: Design (Jan-Feb)..._
```

---

## Multi-Service Queries

### 4. Cancel Flight

**Query:** "Cancel my Turkish Airlines flight"

**Expected Output:**
```
✓ Found your booking confirmation: **Turkish Airlines Booking Confirmation - TK1234**
✓ Found calendar event: **Istanbul → NYC Flight (TK1234)**
✓ **Drafted cancellation email**

Would you like me to send it?
```

---

### 5. Meeting Preparation

**Query:** "Prepare for tomorrow's meeting with Acme Corp"

**Expected Output:**
```
Here's what I found for your meeting:

📅 **Meeting:** Client Meeting - Acme Corp
   Mon 10:00 AM (Zoom)

📧 **Related Emails:** (1 found)
   - Acme Corp - Partnership Proposal

📁 **Related Documents:** (2 found)
   - Acme Corp Partnership Proposal.docx
   - Meeting Notes - Client Calls.docx
```

---

### 6. Calendar with Attendee Filter

**Query:** "What's on my calendar next week where john@company.com is invited?"

**Expected Output:**
```
Found **1** event with john@company.com:

📅 **Meeting with John** - Tue 3:00 PM
   Location: Office
   Attendees: user@example.com, john@company.com
```

---

## Edge Cases

### 7. Ambiguous Query

**Query:** "Move the meeting with John"

**Expected Output:**
```
I found multiple meetings with "John":

1. **Meeting with John** (john@company.com) - Tue 3:00 PM
2. **Meeting with John Miller** (john.miller@company.com) - Wed 10:00 AM

Which meeting would you like to move, and to when?
```

---

### 8. Context-Dependent Query

**Query:** "That email about the proposal"

**Expected Output (with context):**
```
Found the proposal email:

📧 **Acme Corp - Partnership Proposal**
   From: john.smith@acmecorp.com
   _Following our meeting last week, I'm pleased to share our partnership proposal..._
```

**Expected Output (without context):**
```
I found several emails about proposals. Could you be more specific about which proposal or who sent it?
```

---

### 9. Temporal Reasoning

**Query:** "What meetings do I have next Tuesday?"

**Expected Output:**
```
Here are your meetings for Tuesday, January 21st:

📅 **Meeting with John** - 3:00 PM
   Location: Office
```

---

### 10. Invalid Query

**Query:** "asdfghjkl random text"

**Expected Output:**
```
I couldn't understand that query. Could you rephrase it? 

Here are some things I can help with:
- Search your emails, calendar, or files
- Prepare for upcoming meetings
- Cancel or reschedule events
- Draft emails
```

---

## Intent Classification Examples

| Query | Intent | Services | Confidence |
|-------|--------|----------|------------|
| What's on my calendar next week? | search_events | gcal | 0.95 |
| Find emails from sarah@company.com | search_emails | gmail | 0.92 |
| Cancel my Turkish Airlines flight | cancel_flight | gmail, gcal | 0.88 |
| Prepare for Acme meeting | prepare_meeting | gmail, gcal, gdrive | 0.85 |
| Move the meeting with John | ambiguous | gcal | 0.60 |

---

## Performance Expectations

| Query Type | Expected Latency | Target |
|------------|------------------|--------|
| Single service | <300ms | <500ms |
| Multi-service | <600ms | <1000ms |
| With embeddings | <400ms | <500ms |
