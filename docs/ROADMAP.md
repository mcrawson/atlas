# ATLAS Product Studio Roadmap

> **Vision:** Take any idea and turn it into a shipped product that customers can buy, use, or download.

ATLAS is not just a code generator—it's a **product studio** that orchestrates the right tools to create polished, market-ready products.

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ATLAS ORCHESTRATOR                              │
│                                                                              │
│   "I have an idea for a habit tracker app"                                  │
│   "I want to write a productivity book"                                      │
│   "I need a daily planner I can sell"                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DETECT & PLAN                                     │
│                                                                              │
│   • Identify project type (app, book, physical product, website, etc.)      │
│   • Determine required deliverables (code, designs, content, assets)        │
│   • Map out which tools are needed                                          │
│   • Create type-specific project plan                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATE CREATION                                 │
│                                                                              │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│   │  GitHub  │  │  Canva   │  │  Google  │  │  Figma   │  │  Notion  │     │
│   │   Code   │  │  Design  │  │   Docs   │  │    UI    │  │ Content  │     │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            RICH PREVIEW                                      │
│                                                                              │
│   Show the ACTUAL product, not just code:                                   │
│   • App screenshots in device frames                                         │
│   • Book cover + interior pages                                              │
│   • Planner layouts ready for print                                          │
│   • Website live preview                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SHIP IT                                         │
│                                                                              │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│   │   App    │  │  Amazon  │  │  Vercel  │  │  Play    │  │  Gumroad │     │
│   │  Store   │  │   KDP    │  │ /Netlify │  │  Store   │  │  /Etsy   │     │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Product Types & What "Shipped" Means

| Product Type | Example | "Shipped" Means | Key Tools Needed |
|--------------|---------|-----------------|------------------|
| **Mobile App** | Habit tracker | Live in App Store/Play Store | GitHub, Expo, Canva (icons/screenshots), App Store Connect |
| **Book** | Productivity guide | Available on Amazon | Google Docs, Canva (cover), Amazon KDP |
| **Physical Product** | Daily planner | Listed on Amazon/Etsy | Canva (design), Print-on-demand, Marketplace listing |
| **Web App** | SaaS tool | Live website with users | GitHub, Vercel/Netlify, Stripe |
| **Digital Download** | PDF planner | Purchasable on Gumroad/Etsy | Canva (design), Gumroad/Etsy listing |
| **API/Backend** | Service | Deployed and documented | GitHub, Railway/Fly.io, API docs |
| **Chrome Extension** | Productivity tool | In Chrome Web Store | GitHub, Chrome Developer Dashboard |

---

## Integration Map

### Tier 1: Foundation (Unlocks Code-Based Products)
| Integration | Purpose | Products Unlocked | API Status |
|-------------|---------|-------------------|------------|
| **GitHub** | Code storage, version control | All code projects | ✅ Ready |
| **Vercel** | Web deployment | Websites, web apps | ✅ Has API |
| **Netlify** | Web deployment (alternative) | Websites, web apps | ✅ Has API |

### Tier 2: Design (Unlocks Visual Products)
| Integration | Purpose | Products Unlocked | API Status |
|-------------|---------|-------------------|------------|
| **Canva** | Graphics, layouts, covers | Books, planners, marketing | ✅ Has API |
| **Figma** | UI/UX design, prototypes | Apps, websites | ✅ Has API |

### Tier 3: Content (Unlocks Written Products)
| Integration | Purpose | Products Unlocked | API Status |
|-------------|---------|-------------------|------------|
| **Google Docs** | Long-form writing | Books, documentation | ✅ Has API |
| **Notion** | Structured content | Books, courses | ✅ Has API |

### Tier 4: Publishing (Unlocks Shipping)
| Integration | Purpose | Products Unlocked | API Status |
|-------------|---------|-------------------|------------|
| **Amazon KDP** | Book publishing | Books (digital + print) | ⚠️ Partial API |
| **App Store Connect** | iOS publishing | iOS apps | ✅ Has API |
| **Google Play Console** | Android publishing | Android apps | ✅ Has API |
| **Gumroad** | Digital sales | Digital products | ✅ Has API |
| **Etsy** | Marketplace sales | Physical/digital products | ✅ Has API |

### Tier 5: Build & CI (Unlocks Automated Builds)
| Integration | Purpose | Products Unlocked | API Status |
|-------------|---------|-------------------|------------|
| **Expo/EAS** | Mobile app builds | React Native apps | ✅ Has API |
| **GitHub Actions** | CI/CD | All code projects | ✅ Has API |
| **TestFlight** | iOS beta testing | iOS apps | ✅ Via App Store Connect |

---

## Full Platform Ecosystem

*All platforms ATLAS can eventually publish to. Build them as needed - the Integration Layer makes adding new platforms straightforward.*

### Integration Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATLAS Integration Layer                       │
│                                                                  │
│   class PlatformIntegration:                                    │
│       def get_requirements() -> list    # What's needed         │
│       def validate(product) -> bool     # Ready to publish?     │
│       def publish(product) -> result    # Do the thing          │
│       def check_status(id) -> status    # Track progress        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │ gumroad │          │ vercel  │          │  kdp    │
   │   .py   │          │   .py   │          │   .py   │
   └─────────┘          └─────────┘          └─────────┘

Once the layer exists, each new platform = one new file.
```

### Apps & Extensions

| Platform | What It's For | Priority | API | Notes |
|----------|---------------|----------|-----|-------|
| **App Store** | iOS apps | 🔴 High | ✅ Yes | App Store Connect API |
| **Play Store** | Android apps | 🔴 High | ✅ Yes | Google Play Developer API |
| **Amazon Appstore** | Android (Kindle/Fire) | 🟡 Medium | ✅ Yes | Good for Kindle Fire users |
| **Samsung Galaxy Store** | Android (Samsung) | ⚪ Low | ✅ Yes | Large Samsung user base |
| **F-Droid** | Open source Android | ⚪ Niche | Manual | For FOSS projects |
| **Chrome Web Store** | Browser extensions | 🟡 Medium | ✅ Yes | |
| **Firefox Add-ons** | Browser extensions | 🟡 Medium | ✅ Yes | |
| **Safari Extensions** | Safari extensions | ⚪ Low | ✅ Yes | Via App Store Connect |
| **VS Code Marketplace** | VS Code extensions | ⚪ Niche | ✅ Yes | For dev tools |
| **JetBrains Marketplace** | JetBrains plugins | ⚪ Niche | ✅ Yes | For dev tools |

### Books & Written Content

| Platform | What It's For | Priority | API | Notes |
|----------|---------------|----------|-----|-------|
| **Amazon KDP** | Ebooks + Print | 🔴 High | ⚠️ Partial | Largest book marketplace |
| **Draft2Digital** | Multi-store distributor | 🔴 High | ✅ Yes | One API → Apple, Kobo, B&N, etc. |
| **Apple Books** | Ebooks (Apple users) | 🟡 Medium | ✅ Yes | Or use Draft2Digital |
| **Barnes & Noble Press** | Ebooks + Print (Nook) | 🟡 Medium | ⚠️ Limited | Or use Draft2Digital |
| **Kobo Writing Life** | Ebooks (international) | 🟡 Medium | ✅ Yes | Or use Draft2Digital |
| **IngramSpark** | Print distribution | 🟡 Medium | ⚠️ Limited | Gets books into bookstores |
| **Audible/ACX** | Audiobooks | 🟡 Medium | ⚠️ Limited | Requires audio production |
| **Lulu** | Print on demand | ⚪ Low | ✅ Yes | Alternative to KDP Print |
| **Smashwords** | Ebook distribution | ⚪ Low | ✅ Yes | Older platform |

### Digital Products & Downloads

| Platform | What It's For | Priority | API | Notes |
|----------|---------------|----------|-----|-------|
| **Gumroad** | Digital sales (simple) | 🔴 High | ✅ Yes | Great for creators |
| **Etsy** | Digital + physical | 🔴 High | ✅ Yes | Large marketplace |
| **Lemon Squeezy** | Digital + SaaS | 🟡 Medium | ✅ Yes | Modern Gumroad alternative |
| **Payhip** | Digital sales | 🟡 Medium | ✅ Yes | Good margins |
| **Ko-fi** | Tips + digital sales | ⚪ Low | ✅ Yes | Good for creators |
| **Buy Me a Coffee** | Tips + memberships | ⚪ Low | ✅ Yes | Similar to Ko-fi |
| **Itch.io** | Games + creative | ⚪ Niche | ✅ Yes | Great for indie games |

### Physical Products (Print on Demand)

| Platform | What It's For | Priority | API | Notes |
|----------|---------------|----------|-----|-------|
| **Amazon KDP Print** | Books, journals, planners | 🔴 High | ⚠️ Partial | Part of KDP |
| **Printful** | Apparel, mugs, posters | 🔴 High | ✅ Yes | Integrates with Etsy, Shopify |
| **Printify** | Similar to Printful | 🟡 Medium | ✅ Yes | More product options |
| **Redbubble** | Art prints, stickers | 🟡 Medium | ⚠️ Limited | Artist marketplace |
| **Society6** | Home decor, art | ⚪ Low | ⚠️ Limited | Premium feel |
| **Zazzle** | Custom products | ⚪ Low | ✅ Yes | Wide variety |
| **TeePublic** | Apparel | ⚪ Low | ⚠️ Limited | Part of Redbubble |

### Courses & Education

| Platform | What It's For | Priority | API | Notes |
|----------|---------------|----------|-----|-------|
| **Teachable** | Self-hosted courses | 🟡 Medium | ✅ Yes | You own the audience |
| **Podia** | Courses + digital | 🟡 Medium | ✅ Yes | All-in-one platform |
| **Thinkific** | Course platform | 🟡 Medium | ✅ Yes | Similar to Teachable |
| **Udemy** | Course marketplace | ⚪ Low | ⚠️ Limited | They own the audience |
| **Skillshare** | Royalty-based | ⚪ Low | ❌ No | Pay per watch minute |
| **Kajabi** | Premium courses | ⚪ Low | ✅ Yes | Expensive but full-featured |

### Hosting & Deployment

| Platform | What It's For | Priority | API | Notes |
|----------|---------------|----------|-----|-------|
| **Vercel** | Frontend/Next.js | 🔴 High | ✅ Yes | Best for React/Next |
| **Netlify** | Frontend/static | 🔴 High | ✅ Yes | Great free tier |
| **Railway** | Backend + databases | 🔴 High | ✅ Yes | Simple full-stack |
| **Fly.io** | Global edge deployment | 🟡 Medium | ✅ Yes | Fast everywhere |
| **Render** | Full stack hosting | 🟡 Medium | ✅ Yes | Heroku alternative |
| **Cloudflare Pages** | Static + edge | 🟡 Medium | ✅ Yes | Fast + free |
| **Firebase Hosting** | Google ecosystem | 🟡 Medium | ✅ Yes | Good with Firebase |
| **AWS Amplify** | AWS ecosystem | ⚪ Low | ✅ Yes | More complex |
| **DigitalOcean App Platform** | Simple deployment | ⚪ Low | ✅ Yes | Good pricing |
| **Heroku** | Classic PaaS | ⚪ Low | ✅ Yes | No longer free |

### Marketing & Launch

| Platform | What It's For | Priority | API | Notes |
|----------|---------------|----------|-----|-------|
| **Product Hunt** | Launch announcements | 🟡 Medium | ✅ Yes | Great for visibility |
| **Indie Hackers** | Community/feedback | ⚪ Low | ❌ No | Manual posting |
| **Medium** | Content marketing | 🟡 Medium | ✅ Yes | Articles/SEO |
| **Substack** | Newsletter/audience | 🟡 Medium | ✅ Yes | Build email list |
| **ConvertKit** | Email marketing | ⚪ Low | ✅ Yes | Creator-focused |
| **Mailchimp** | Email marketing | ⚪ Low | ✅ Yes | More traditional |

### Social Media (For Announcements)

| Platform | What It's For | Priority | API | Notes |
|----------|---------------|----------|-----|-------|
| **Twitter/X** | Announcements | 🟡 Medium | ⚠️ Paid | API now costs money |
| **LinkedIn** | Professional audience | ⚪ Low | ⚠️ Limited | Good for B2B |
| **Instagram** | Visual products | ⚪ Low | ⚠️ Limited | Good for physical products |
| **TikTok** | Short-form video | ⚪ Low | ✅ Yes | Growing platform |
| **YouTube** | Video content | ⚪ Low | ✅ Yes | For tutorials/demos |

---

## Platform Selection by Product Type

*Which platforms to prioritize based on what you're building:*

### Mobile App
| Phase | Platforms |
|-------|-----------|
| Build | GitHub, Expo/EAS |
| Preview | Device mockups, App Store preview |
| Ship | App Store, Play Store |
| Optional | Amazon Appstore, Product Hunt |

### Book (Digital + Print)
| Phase | Platforms |
|-------|-----------|
| Write | Google Docs, Notion |
| Design | Canva (cover) |
| Ship | Amazon KDP (or Draft2Digital for multi-store) |
| Optional | Gumroad (direct sales), Audible (audiobook) |

### Physical Planner/Journal
| Phase | Platforms |
|-------|-----------|
| Design | Canva |
| Ship | Amazon KDP Print, Etsy |
| Optional | Printful (for custom options) |

### Digital Product (PDF, Template, etc.)
| Phase | Platforms |
|-------|-----------|
| Design | Canva |
| Ship | Gumroad, Etsy |
| Optional | Payhip, Lemon Squeezy |

### Web App / SaaS
| Phase | Platforms |
|-------|-----------|
| Build | GitHub |
| Deploy | Vercel, Railway |
| Optional | Product Hunt (launch), Stripe (payments) |

### Course
| Phase | Platforms |
|-------|-----------|
| Content | Google Docs, Notion |
| Video | YouTube (unlisted) or direct upload |
| Ship | Teachable, Podia |
| Optional | Gumroad (simpler), Udemy (marketplace) |

---

## Rich Preview System

When Tinker finishes building, the preview should show **what customers will see**, not just code.

### Preview by Product Type

#### Mobile App Preview
```
┌─────────────────────────────────────────────────────────────────┐
│  📱 Habit Tracker App                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ [App Icon]   │  │ [Screenshot] │  │ [Screenshot] │          │
│  │   128x128    │  │  Home Screen │  │  Add Habit   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  App Store Listing Preview:                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ⭐⭐⭐⭐⭐  Habit Tracker - Build Better Habits          │   │
│  │ [Screenshot carousel]                                    │   │
│  │ Track your daily habits with ease...                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [View Code] [View in Expo] [Submit to App Store]              │
└─────────────────────────────────────────────────────────────────┘
```

#### Book Preview
```
┌─────────────────────────────────────────────────────────────────┐
│  📚 The Productivity Playbook                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────────────────────────────┐    │
│  │              │  │ Chapter 1: The Morning Routine        │    │
│  │ [Book Cover] │  │                                        │    │
│  │              │  │ The way you start your day determines  │    │
│  │  PRODUCTIVITY│  │ how the rest of it unfolds...          │    │
│  │  PLAYBOOK    │  │                                        │    │
│  │              │  │ [Sample interior page layout]          │    │
│  └──────────────┘  └──────────────────────────────────────┘    │
│                                                                  │
│  Amazon Listing Preview:                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ The Productivity Playbook                    $14.99      │   │
│  │ ⭐⭐⭐⭐☆ (Preview)  |  Paperback  |  Kindle            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [Edit in Google Docs] [Update Cover in Canva] [Publish to KDP]│
└─────────────────────────────────────────────────────────────────┘
```

#### Physical Planner Preview
```
┌─────────────────────────────────────────────────────────────────┐
│  📅 2026 Daily Planner                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │   Cover    │ │  Monthly   │ │   Weekly   │ │   Notes    │   │
│  │            │ │  Spread    │ │   Spread   │ │   Page     │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│                                                                  │
│  Print Specifications:                                          │
│  • Size: 6" x 9"                                                │
│  • Pages: 248                                                    │
│  • Paper: 90gsm cream                                           │
│  • Binding: Perfect bound                                       │
│                                                                  │
│  [Edit in Canva] [Download Print PDF] [Publish to Amazon]      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Milestones & Phases

### Phase 1: Foundation ✅ (Partially Complete)
*Goal: Type-aware pipeline that knows what it's building*

- [x] Project type detection (app vs book vs website vs etc.)
- [x] Type-specific idea conversations
- [x] Agent pipeline (Buzz → Sketch → Tinker → Oracle → Launch)
- [x] Slack integration for idea capture
- [ ] Type-aware planning (Sketch adapts output format to project type)
- [ ] Type-aware building (Tinker knows deliverables per type)

### Phase 2: GitHub Integration
*Goal: Code actually lands somewhere real*

- [ ] Create GitHub repos from ATLAS
- [ ] Push generated code automatically
- [ ] Create proper project structure
- [ ] Initialize with README, .gitignore, etc.
- [ ] Support for private repos

### Phase 3: Design Integration (Canva)
*Goal: Visual products get real designs*

- [ ] Canva API integration
- [ ] Template selection by product type
- [ ] Generate covers (books, planners)
- [ ] Generate marketing assets
- [ ] Export production-ready files
- [ ] Embed Canva previews in ATLAS

### Phase 4: Rich Preview System
*Goal: See the actual product, not just code*

- [ ] Preview renderer by product type
- [ ] Device frame mockups for apps
- [ ] Book/planner page previews
- [ ] Website live preview
- [ ] App Store listing preview
- [ ] Amazon listing preview

### Phase 5: Content Integration
*Goal: Long-form content gets proper tools*

- [ ] Google Docs integration for book writing
- [ ] Chapter-by-chapter writing workflow
- [ ] Notion integration (alternative)
- [ ] Export to various formats (PDF, EPUB, etc.)

### Phase 6: Automated Deployment (Web)
*Goal: Websites go live automatically*

- [ ] Vercel integration
- [ ] Auto-deploy from GitHub
- [ ] Custom domain support
- [ ] Environment variables management
- [ ] Deployment status in ATLAS

### Phase 7: Mobile App Building
*Goal: Apps can be built and tested*

- [ ] Expo/EAS integration
- [ ] Cloud builds for iOS and Android
- [ ] TestFlight upload (iOS)
- [ ] Internal testing (Android)
- [ ] Build status tracking

### Phase 8: Publishing Integrations
*Goal: Products can be shipped to customers*

- [ ] Amazon KDP integration (books)
- [ ] App Store Connect integration
- [ ] Google Play Console integration
- [ ] Gumroad integration (digital products)
- [ ] Etsy integration (physical/digital)

### Phase 9: End-to-End Workflows
*Goal: One-click from idea to shipped product*

- [ ] "Ship to App Store" button
- [ ] "Publish to Amazon" button
- [ ] "Go Live" button for websites
- [ ] Status tracking through review processes
- [ ] Notification when products are live

---

## What Each Agent Does (Updated Vision)

### Buzz (Communications)
- Slack integration for idea capture ✅
- Notifications across all channels
- Status updates during builds
- "Your product is live!" celebrations

### Sketch (Planning)
**Becomes type-aware:**
- App: Plans screens, features, architecture
- Book: Plans chapters, outline, key messages
- Planner: Plans sections, layouts, page types
- Website: Plans pages, components, user flows

### Tinker (Building)
**Becomes an orchestrator:**
- Knows which tools to use for each deliverable
- Code → GitHub
- Designs → Canva
- Content → Google Docs
- Assembles all pieces into cohesive product

### Oracle (Verification)
**Expands beyond code:**
- Code: Syntax, security, best practices ✅
- Design: Brand consistency, print specs, accessibility
- Content: Consistency, accuracy, tone
- Listings: Guidelines compliance (App Store, Amazon)

### Launch (Shipping)
**Actually ships, not just instructions:**
- Deploys websites to Vercel
- Uploads apps to TestFlight/Play Console
- Publishes books to Amazon KDP
- Lists products on Gumroad/Etsy
- Tracks review/approval status

---

## Success Metrics

How we know ATLAS is working:

| Metric | Target |
|--------|--------|
| Idea → Shipped time | < 1 week for simple products |
| Manual steps required | Minimal (only approvals) |
| Products shipped | Track total products launched |
| Revenue generated | Optional: track sales if integrated |

---

## Technical Considerations

### API Keys Needed
```bash
# Current
OPENAI_API_KEY=...
SLACK_BOT_TOKEN=...
SLACK_SIGNING_SECRET=...

# Phase 2: GitHub
GITHUB_TOKEN=...

# Phase 3: Design
CANVA_API_KEY=...

# Phase 5: Content
GOOGLE_DOCS_CREDENTIALS=...

# Phase 6: Deployment
VERCEL_TOKEN=...

# Phase 7: Mobile
EXPO_TOKEN=...
APPLE_APP_STORE_CONNECT_KEY=...
GOOGLE_PLAY_SERVICE_ACCOUNT=...

# Phase 8: Publishing
AMAZON_KDP_CREDENTIALS=...  # If available
GUMROAD_API_KEY=...
ETSY_API_KEY=...
```

### Database Additions
- Integration credentials storage
- External resource links (GitHub repos, Canva designs, etc.)
- Publishing status tracking
- Asset management

### Adding New Platforms (Future)

Once the Integration Layer is built, adding a new platform is simple:

```python
# atlas/integrations/platforms/newplatform.py

from atlas.integrations.base import PlatformIntegration

class NewPlatformIntegration(PlatformIntegration):
    name = "newplatform"
    icon = "🆕"

    def get_requirements(self):
        return ["API key", "Account setup"]

    def validate(self, product):
        # Check if product meets platform requirements
        return True

    async def publish(self, product):
        # Call platform API
        return {"success": True, "url": "..."}

    async def check_status(self, submission_id):
        return {"status": "published"}
```

Then register in config:
```python
PLATFORMS = {
    "newplatform": NewPlatformIntegration,
    # ... other platforms
}
```

**Estimated effort per platform:** 2-4 hours once the base layer exists.

---

## Next Steps

1. **Immediate:** Complete Phase 1 (type-aware pipeline)
2. **Next session:** Start Phase 2 (GitHub integration)
3. **Design milestone:** Canva integration for visual products
4. **Shipping milestone:** First product published through ATLAS

---

*Last updated: 2026-03-05*
*This is a living document - update as we progress*
