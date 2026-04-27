# Mock Sales Data

The n8n workflow injects this mock sales knowledge base in the `Mock_Sales_KB` node before `Researcher_Agent`.

Use this mock inquiry for the primary sales demo:

```text
Subject: Enterprise pricing inquiry

Hi, we are a 50-person support team evaluating automation for Gmail inquiries.
Can you share enterprise pricing, setup timeline, and a demo slot?
```

The workflow should classify it as `sales_inquiry`, use the mock sales data, qualify it as a warm lead, draft a pricing/demo reply, send through Gmail when `GMAIL_SEND_MODE=auto`, and append the execution row to Google Sheets.

Mock product data:

```text
Company: HestaBot Automation Platform
Product: Multi-agent customer inquiry automation for Gmail, Google Sheets, Google Drive knowledge retrieval, and workflow monitoring.
Starter: INR 24,000/month; up to 10 users; Gmail inquiry automation, basic dashboard, email support.
Growth: INR 75,000/month; up to 50 users; 5-agent inquiry workflow, Google Sheets logging, workflow console, priority support.
Enterprise: custom, starting at INR 1,80,000/month; 50+ users; dedicated success manager, SLA, custom integrations, security review.
Demo booking: 30-minute discovery/demo call within 2 business days.
Onboarding: 5-7 business days for Gmail and Sheets; 10-14 business days with Drive KB and custom routing.
Annual discount: 15%.
```
