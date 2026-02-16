# n8n Workflow: Friction Finder Report Generation

This workflow automatically generates executive reports when new friction reports are submitted through the Voice Intake feature.

## Workflow Overview

**Trigger:** Webhook receives notification from Friction Finder API
**Output:** AI-generated report with summary and recommendations, stored in ReportRun table

## Workflow Nodes

### 1. Webhook Trigger
**Type:** Webhook
**Authentication:** Header Auth

**Configuration:**
- HTTP Method: POST
- Authentication: Header Auth
- Header Name: `x-webhook-secret`
- Header Value: `{{$env.N8N_WEBHOOK_SECRET}}`

**Expected Payload:**
```json
{
  "interview_id": 123,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "respondent_id": 45
}
```

### 2. Get Interview Details
**Type:** HTTP Request
**Method:** GET
**URL:** `{{$env.API_BASE_URL}}/interviews/{{$json.interview_id}}`

**Headers:**
- `x-app-password`: `{{$env.APP_PASSWORD}}`

**Output:** Interview data including transcript, summary, metadata

### 3. Get Pain Points
**Type:** HTTP Request
**Method:** GET
**URL:** `{{$env.API_BASE_URL}}/pain-points?interview_id={{$json.interview_id}}`

**Headers:**
- `x-app-password`: `{{$env.APP_PASSWORD}}`

**Output:** Array of pain points with scoring data

### 4. Check If Pain Points Exist
**Type:** IF Node

**Condition:** `{{$json.length > 0}}`

**True Branch:** Continue to AI analysis
**False Branch:** End workflow (no pain points to analyze)

### 5. AI Summarization
**Type:** OpenAI Chat Model (or equivalent)

**Prompt Template:**
```
You are an operations analyst reviewing friction reports from employees.

INTERVIEW SUMMARY:
{{$node["Get Interview Details"].json["summary_text"]}}

PAIN POINTS IDENTIFIED:
{{$node["Get Pain Points"].json.map(p => `- ${p.title} (${p.category}): ${p.description}
  Impact: ${p.impact_hours_per_week}h/week, Effort: ${p.effort_score}/5, Priority: ${p.priority_score}
`).join('\n')}}

Please provide:
1. A concise executive summary (2-3 sentences) of the key operational friction points
2. Top 3 recommended actions in order of priority

Format your response as JSON:
{
  "summary": "...",
  "recommendations": [
    {"priority": 1, "action": "...", "rationale": "..."},
    {"priority": 2, "action": "...", "rationale": "..."},
    {"priority": 3, "action": "...", "rationale": "..."}
  ]
}
```

**Model:** GPT-4o-mini (or equivalent)
**Temperature:** 0.3
**Response Format:** JSON

### 6. Parse AI Response
**Type:** Code Node (JavaScript)

**Code:**
```javascript
// Extract JSON from AI response
const aiResponse = $input.item.json.choices[0].message.content;
const parsed = JSON.parse(aiResponse);

return {
  json: {
    summary: parsed.summary,
    recommendations: parsed.recommendations,
    interview_id: $node["Webhook"].json.interview_id,
    session_id: $node["Webhook"].json.session_id
  }
};
```

### 7. Generate PDF Report (Optional)
**Type:** HTTP Request
**Method:** GET
**URL:** `{{$env.API_BASE_URL}}/report.pdf`

**Headers:**
- `x-app-password`: `{{$env.APP_PASSWORD}}`

**Binary Data:** Yes
**Output:** PDF blob

**Note:** This step is optional. If you want to include PDF generation, you can store the PDF somewhere (S3, Google Drive, etc.) and pass the URL to the next step.

### 8. Attach Report to Database
**Type:** HTTP Request
**Method:** POST
**URL:** `{{$env.API_BASE_URL}}/report/attach`

**Headers:**
- `Content-Type`: `application/json`
- `x-webhook-secret`: `{{$env.N8N_WEBHOOK_SECRET}}`

**Body:**
```json
{
  "interview_id": {{$node["Webhook"].json.interview_id}},
  "session_id": "{{$node["Webhook"].json.session_id}}",
  "summary": "{{$node["Parse AI Response"].json.summary}}",
  "recommendations_json": {{$json["recommendations"]}},
  "source": "n8n",
  "pdf_path_or_url": null
}
```

### 9. (Optional) Send Slack Notification
**Type:** Slack
**Action:** Send Message

**Channel:** `#friction-reports`
**Message:**
```
🎯 New Friction Report Generated

Session ID: {{$node["Webhook"].json.session_id}}
Interview ID: {{$node["Webhook"].json.interview_id}}

Summary: {{$node["Parse AI Response"].json.summary}}

View full report: {{$env.WEB_APP_URL}}/pain-points?interview_id={{$node["Webhook"].json.interview_id}}
```

### 10. (Optional) Send Email
**Type:** Email (Send)

**To:** `ops-team@company.com`
**Subject:** `New Friction Report - Session {{$node["Webhook"].json.session_id}}`
**Body:**
```html
<h2>Friction Report Generated</h2>

<p><strong>Summary:</strong><br/>
{{$node["Parse AI Response"].json.summary}}</p>

<h3>Top Recommendations:</h3>
<ol>
{{$node["Parse AI Response"].json.recommendations.map(r => `<li><strong>${r.action}</strong><br/>${r.rationale}</li>`).join('')}}
</ol>

<p><a href="{{$env.WEB_APP_URL}}/report">View Full Report</a></p>
```

## Environment Variables Required

Configure these in your n8n environment:

```env
API_BASE_URL=http://localhost:8000
APP_PASSWORD=changeme
N8N_WEBHOOK_SECRET=your_secret_here
WEB_APP_URL=http://localhost:3000
OPENAI_API_KEY=your_openai_key (if using OpenAI node)
```

## Workflow Execution Flow

```
Webhook Trigger
    ↓
Get Interview Details (HTTP)
    ↓
Get Pain Points (HTTP)
    ↓
Check If Pain Points Exist (IF)
    ↓ (true)
AI Summarization (OpenAI/LLM)
    ↓
Parse AI Response (Code)
    ↓
Attach Report (HTTP POST)
    ↓
[Optional] Slack/Email Notifications
```

## Error Handling

- All HTTP nodes should have "Continue On Fail" enabled
- Add error branches to handle:
  - API authentication failures
  - Missing interview/pain point data
  - AI API failures or invalid JSON responses
  - Report attachment failures

## Testing

1. Import the workflow from `examples/n8n_workflow.json`
2. Configure environment variables
3. Activate the workflow
4. Test webhook URL with curl:
```bash
curl -X POST "https://your-n8n-instance.com/webhook/friction-finder" \
  -H "Content-Type: application/json" \
  -H "x-webhook-secret: your_secret" \
  -d '{"interview_id": 1, "session_id": "test-123", "respondent_id": 1}'
```

## Production Considerations

- **Rate Limiting:** Add delays if processing many reports simultaneously
- **Retry Logic:** Configure HTTP request retries for transient failures
- **Monitoring:** Set up n8n workflow execution monitoring
- **Security:** Never commit webhook secrets to git
- **Scalability:** Consider using n8n queues for high-volume scenarios
