# app/policies/classification_policies.md

## Overview
This document defines comprehensive classification rules for evaluating publisher websites for affiliate marketing campaigns. All classifications must reference these policies.

---

## Policy 1: Cashback Sites

### Definition
Websites that return a percentage of purchase value to users through affiliate commission sharing.

### Key Indicators
- **Primary Terms**: "cash back", "cashback", "rebate", "rewards program", "earn money back", "cash rewards"
- **Features**:
  - Lists of partner stores with specific cashback percentages
  - User account system with earning tracking
  - Withdrawal thresholds and payout methods
  - Browser extensions for automatic cashback
  - Referral programs

### Business Model
Affiliate commissions split with users. The site earns commission from purchases and passes a portion back to the user.

### Examples
- **Legitimate**: Rakuten, TopCashback, Swagbucks, BeFrugal, Ibotta
- **Not Cashback**: Coupon sites (different model), price comparison sites

### Decision Guidelines
- **Flag as cashback**: YES if primary business model is rewarding purchases
- **Score Impact**: -10 to -20 (lower than standard e-commerce)
- **Confidence**: High if cashback rates and store listings present

### Edge Cases
- Hybrid coupon+cashback sites: Flag as cashback
- Browser extensions only: Still cashback
- Crypto rewards: Still cashback

---

## Policy 2: Adult Content

### Definition
Websites containing explicit sexual content, adult entertainment, escort services, or mature dating services intended for audiences 18+.

### Key Indicators
- **Primary Terms**: "xxx", "adult", "porn", "escort", "sex", "nude", "nsfw", "18+", "mature", "explicit"
- **Features**:
  - Age verification gate (must confirm 18+)
  - Explicit imagery or video content
  - Adult dating or hookup services
  - Escort directories
  - Adult toys with explicit descriptions

### NOT Adult Content (Edge Cases)
- Sexual health education (e.g., Planned Parenthood) - NOT adult
- Mainstream dating apps (e.g., Tinder, Bumble) - NOT adult
- Medical information about reproductive health - NOT adult
- Art with nudity (museum sites) - NOT adult
- Lingerie e-commerce (without explicit content) - NOT adult

### Decision Guidelines
- **Flag as adult**: YES if primary purpose is adult entertainment or explicit content
- **Score Impact**: 0 (automatically rejected)
- **Confidence**: High if explicit content confirmed

---

## Policy 3: Gambling

### Definition
Websites offering real money wagering on games of chance or skill, including casinos, sports betting, poker, and lotteries.

### Key Indicators
- **Primary Terms**: "casino", "bet", "poker", "slot", "jackpot", "roulette", "blackjack", "sportsbook", "wagering", "odds", "betting"
- **Features**:
  - Deposit bonuses and wagering requirements
  - Live betting odds
  - Casino games with real money
  - Gaming licenses (Malta, Gibraltar, Curacao, UKGC)
  - Responsible gambling messaging
  - KYC verification

### Types
- Online casinos, sports betting platforms, poker rooms with cash games
- Lottery and bingo sites, esports betting, crypto gambling sites

### NOT Gambling (Edge Cases)
- Social casinos (no real money) - NOT gambling
- Fantasy sports without cash prizes - NOT gambling
- Gambling affiliate sites (promoting gambling) - STILL flag as gambling

### Decision Guidelines
- **Flag as gambling**: YES if real money wagering is offered
- **Score Impact**: 0 (automatically rejected)
- **Confidence**: High if deposit options and gambling terms present

---

## Policy 4: Agency or Introductory Sites

### Definition
Websites with minimal original content that primarily serve as intermediaries, redirecting users to other sites for affiliate commissions.

### Key Indicators
- **Primary Terms**: "best", "top 10", "compare", "review", "deals", "discount"
- **Characteristics**:
  - Thin content (fewer than 500 words of unique text)
  - Heavy affiliate links (outbound > inbound)
  - Landing pages with immediate calls-to-action
  - No original research or in-depth reviews
  - Copied or spun content from other sources

### Structural Patterns
- List posts ("Top 10 Best...")
- Comparison tables with affiliate links
- "Best X for Y" format pages

### NOT Agency (Legitimate Sites)
- Genuine review sites with original, detailed reviews
- Comparison shopping with original content
- News sites with journalistic standards
- Direct e-commerce with original product descriptions

### Quality Assessment
- **High** (Legitimate): Original content, expert opinions, in-depth research → No penalty
- **Medium** (Acceptable): Good content but heavy affiliate links → -15 points
- **Low** (Flag): Thin content, no original value, heavy redirects → -30 points, flagged

### Decision Guidelines
- **Flag as agency**: YES if site exists primarily to redirect to affiliate offers
- **Score Impact**: -20 to -40 based on quality
- **Confidence**: High if content is clearly aggregated

---

## Policy 5: Scam or Low Quality

### Definition
Sites with deceptive practices, fraudulent claims, or extremely poor quality that would damage brand reputation.

### Deceptive Practices (High Priority)
- **Prize Claims**: "You won", "Congratulations, you're a winner"
- **False Scarcity**: "Limited time offer", "Only X left", "Act now" (excessive)
- **Fake Endorsements**: Celebrity endorsements without permission
- **Medical Fraud**: "Cure cancer", "Miracle weight loss"
- **Financial Fraud**: "Make $10,000/month", "Get rich quick"

### Technical Issues
- Excessive pop-ups, especially on page load
- Multiple redirects before reaching content
- Forced downloads without consent
- Fake virus warnings

### Content Quality Issues
- Frequent spelling/grammar errors
- Auto-generated gibberish
- Stolen content from other sites
- Thin content: fewer than 200 words of meaningful content

### Missing Legitimacy Signals
- No contact information (email, phone, address)
- No privacy policy (required by law)
- No about page (anonymous ownership)
- No SSL certificate (not HTTPS)

### Decision Guidelines
- **Flag as scam/low quality**: YES if 3+ medium red flags or 1 high red flag
- **Score Impact**: 0-30 (severely penalized)
- **Confidence**: Medium to High based on severity

---

## Policy 6: Legitimate E-commerce

### Definition
Sites selling products or services directly with original content, clear business model, and legitimate operations.

### Positive Indicators
- Business information: physical address, contact details, company registration
- Legal pages: privacy policy, terms of service, returns policy
- Original content: product descriptions, blog posts, reviews
- Secure checkout: HTTPS, payment gateway logos
- Customer reviews: real user reviews
- Active customer support: live chat, email, phone support

### Quality Assessment
- **Excellent** (90-100): All trust signals, original content, strong brand
- **Good** (70-89): Most trust signals, good content
- **Acceptable** (50-69): Basic trust signals, decent content
- **Poor** (30-49): Missing some signals, thin content

### Decision Guidelines
- **NOT flagged**: Desirable publisher sites
- **Score Impact**: 70-100 based on quality
- **Confidence**: High if multiple trust signals present

---

## Policy 7: News, Blog and Editorial Sites

### Definition
Sites with original journalistic or editorial content, regular publishing schedule, and clear authorship.

### Indicators
- Regular updates: recent articles (last 7 days)
- Author bylines: named authors with bios
- Editorial standards: fact-checking, corrections policy
- Comments and engagement: user interaction
- Contact info: editorial contact, masthead

### Quality Assessment
- **Excellent** (90-100): Professional journalism, fact-checked, regular updates
- **Good** (70-89): Original content, regular posting
- **Acceptable** (50-69): Personal blog, occasional updates

### Decision Guidelines
- **NOT flagged**: Quality editorial content is valuable
- **Score Impact**: 80-100 for high-quality publications
- **Confidence**: High if journalistic standards visible

---

## Scoring Guidelines

### Automatic Rejections (Score = 0)
- Gambling sites
- Adult content sites
- Confirmed scam sites

### Score Adjustments
- Cashback: -10 to -20
- Agency/Low quality: -20 to -40
- Missing trust signals: -5 each
- Poor content quality: -10 to -30
- Scam indicators: -50 to -100

### Bonus Points
- Contact page: +5 | Privacy policy: +5 | About page: +5
- SSL/HTTPS: +5 | Customer reviews: +5 | Active social media: +5

### Final Score Ranges
- 90-100: Excellent → Approve for premium campaigns
- 70-89: Good → Approve for standard campaigns
- 50-69: Acceptable → Approve with monitoring
- 30-49: Poor → Flag for review
- 0-29: Unacceptable → Reject automatically

---

## Classification Hierarchy

When multiple categories apply, use this priority order:

1. **Gambling or Adult** → Immediate reject (score 0)
2. **Scam** → Reject (score 0-30)
3. **Cashback** → Accept with flag (score 70-80)
4. **Agency** → Flag for review (score 40-60)
5. **Legitimate** → Approve (score 70-100)
