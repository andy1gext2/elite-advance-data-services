# Master Product Prompt — AI Marketing & Reputation Management SaaS

> Verbatim source of truth, transcribed from the original brief. This is the product spec; architecture/roadmap docs derive from it.

## Project Overview
A production-ready SaaS platform that is an AI-powered Marketing and Reputation Management Operating System for businesses. It becomes the owner's AI Marketing Manager, Social Media Manager, and Reputation Manager — replacing multiple tools with one intelligent platform. Scalable to thousands of businesses, modular so new AI features can be added later.

## Primary Mission
Help businesses: grow online presence · automatically generate content · maintain a strong reputation · increase engagement · save hundreds of hours · provide AI-driven insights · increase acquisition and retention.

## Core Features

### 1. AI Social Media Manager
Generate posts for Instagram, Facebook, LinkedIn, X, Threads, Google Business Profile; SEO blog articles; email newsletters; SMS campaigns; promotional / seasonal / holiday / event campaigns; trend analysis.

User provides: business description, industry, target audience, desired tone, brand voice, goals, promotions, website. AI creates professional, tailored content.

### Content Repurposing
One idea → Instagram → Facebook → LinkedIn → Threads → X → Blog → Email → SMS → short video script → caption variations → hashtag suggestions → CTA variants. Each version **optimized per platform**, not copied.

### AI Content Calendar
Weekly / monthly / quarterly / annual plans. Recommends best posting time, best platform, trending ideas, industry-specific content, holiday opportunities, educational posts, sales promotions, community engagement, customer appreciation.

### Social Media Scheduling
Schedule, auto-publish, draft, approve, team collaboration, publishing calendar, bulk scheduling, automatic reposting, cross-platform publishing.

### Reputation Management
Monitor Google Reviews, Facebook Reviews, and additional platforms (expandable). Detect new reviews; AI responses (positive & negative); escalation recommendations; sentiment analysis; review/rating trends; review growth; satisfaction insights; common complaints & compliments; keyword frequency; monthly reputation reports.

### AI Business Insights
Acts like a business consultant. "How is my business doing?" → follower/reach growth, engagement rate, review growth, average rating, best/worst posts, website traffic, lead trends, common compliments/complaints, recommendations, marketing opportunities, content & campaign recommendations, competitor observations (future).

### AI Recommendations (examples)
"Post tomorrow at 9 AM." · "Customers respond well to educational content." · "Google reviews up 22%." · "People love your customer service." · "Customers complain about response times." · "Create another testimonial post." · "You haven't posted in 6 days." · "Respond to these 3 unanswered reviews."

### Dashboard
Modern enterprise dashboard: follower growth, review growth, reputation score, average rating, engagement, top platforms, latest reviews, scheduled posts, AI recommendations, campaign performance, monthly analytics, real-time KPIs, beautiful graphs, dark/light mode, responsive.

## Integrations
OAuth-based. Supported: Instagram, Facebook, LinkedIn, Google Business Profile, TikTok, YouTube, X, Threads. Future: Pinterest, Snapchat, Reddit, CRM, email providers, SMS providers, advertising platforms.

## AI Architecture
Do NOT rely on one AI model — build an orchestration layer:
`User Request → AI Router → Task Classification → Specialized AI Module → Platform APIs → Database → Dashboard`.
Modules: Content Generation, Marketing Strategy, Review Responses, Sentiment Analysis, Business Insights, Analytics Summaries, Campaign Planning, SEO; future: Video Gen, Image Gen, Voice Assistant. Backend must be provider-agnostic (swap AI providers without changing business logic).

## Software Architecture
- **Frontend:** React, Next.js, TypeScript, Tailwind CSS, responsive, modern UI.
- **Backend:** Python, FastAPI, REST, Authentication, OAuth, JWT.
- **Database:** PostgreSQL, Redis.
- **Background:** Celery, queue workers, cloud storage, analytics pipeline.
- **API layer / connectors:** Instagram, Facebook, LinkedIn, Google, TikTok, YouTube, X — each isolated so API changes affect only one module.

## Internal Database (never rely on AI memory)
Store: business profile, brand voice, products, services, target audience, posting schedule, social accounts, review history, marketing campaigns, performance metrics, brand colors, logo, approved hashtags, custom prompts, team members, permissions, historical analytics. AI uses **RAG** — retrieve business data before generating.

## Scalability
Design for 10,000+ businesses; millions of posts/reviews/analytics events. Horizontal scaling, containerization, load balancing, CDN, caching, rate limiting, monitoring, logging, high availability.

## Security
OAuth auth, role-based permissions, encrypted secrets, encrypted API tokens, HTTPS, audit logs, SOC 2 / GDPR / CCPA readiness, secure API gateway.

## Subscription Plans
Starter · Professional · Growth · Enterprise. Feature gating controls: number of users, connected social accounts, locations, AI usage allowances, advanced analytics, white labeling, priority support, enterprise integrations.

## Future Roadmap
AI images/videos, AI ad creation & optimization, competitor analysis, trend prediction, local SEO, website audits, marketing ROI forecasting, CRM integration, lead nurturing, email/SMS automation, voice AI, phone AI, appointment booking, workflow automation, integrations marketplace, mobile apps, white-label reseller program, agency dashboard, multi-location management.

## Design Philosophy
Premium, modern, intelligent. Avoid clutter. Prioritize speed. Smooth animations. Actionable insights over raw data. Make the owner feel they hired an entire AI-powered marketing department.

## Overall Objective
Enterprise-grade platform combining AI content creation, social management, scheduling, analytics, review monitoring, sentiment analysis, business intelligence, and recommendations in one scalable SaaS. Modular, provider-agnostic, cloud-native, secure, extensible. Every major component replaceable without a rewrite.
