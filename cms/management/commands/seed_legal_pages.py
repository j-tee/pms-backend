"""
Seed Legal Pages Command

Creates the required public legal pages for AdSense compliance:
- Privacy Policy
- Terms of Service
- FAQ
- About Us
- Contact Information

These pages are publicly accessible without authentication.

Usage:
    python manage.py seed_legal_pages              # Seed all pages
    python manage.py seed_legal_pages --force      # Force update existing pages
    python manage.py seed_legal_pages --pages privacy_policy terms_of_service  # Specific pages
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from cms.models import ContentPage, ContentPageRevision

User = get_user_model()

# =============================================================================
# PAGE CONTENT DEFINITIONS
# Updated: January 25, 2026
# =============================================================================

LEGAL_PAGES = {
    'privacy_policy': {
        'title': 'Privacy Policy',
        'slug': 'privacy-policy',
        'meta_description': 'Privacy Policy for YEA Poultry Management System - How we collect, use, and protect your data.',
        'meta_keywords': 'privacy policy, data protection, YEA PMS, Ghana poultry, personal information',
        'excerpt': 'This Privacy Policy describes how the YEA Poultry Management System collects, uses, and protects your personal information.',
        'content': """## Introduction

Welcome to the Youth Entrepreneurship in Agriculture (YEA) Poultry Management System. We are committed to protecting your personal information and your right to privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform.

## Information We Collect

### Personal Information
We collect personal information that you voluntarily provide when you:
- Register for an account
- Apply for the YEA program
- Use our marketplace services
- Contact us for support
- Subscribe to our newsletter

This information may include:
- Name and contact information (email, phone number, address)
- Farm details and location
- Business information
- Financial information for transactions
- Government-issued identification (for verification purposes)

### Automatically Collected Information
We automatically collect certain information when you visit our platform:
- IP address and device information
- Browser type and version
- Usage data and analytics
- Cookies and similar tracking technologies

## How We Use Your Information

We use your information for the following purposes:
- **Service Delivery:** To provide and maintain our platform services
- **Account Management:** To create and manage your account
- **Communication:** To send you updates, notifications, and support messages
- **Analytics:** To understand how our platform is used and improve our services
- **Compliance:** To comply with legal obligations and government requirements
- **Marketing:** To send promotional materials (with your consent)

## Data Sharing

We may share your information with:
- Government agencies as required for the YEA program
- Service providers who assist in operating our platform
- Other users (limited marketplace information)
- Legal authorities when required by law

We do NOT sell your personal information to third parties.

## Data Security

We implement appropriate technical and organizational security measures to protect your personal information, including:
- Encryption of data in transit and at rest
- Access controls and authentication
- Regular security assessments
- Employee training on data protection

## Your Rights

You have the right to:
- Access your personal data
- Request correction of inaccurate data
- Request deletion of your data (subject to legal requirements)
- Object to certain processing of your data
- Request data portability

To exercise these rights, contact us at alphalogiquetechnologies@gmail.com.

## Cookies

We use cookies and similar tracking technologies to improve your experience. You can control cookie settings through your browser. Types of cookies we use:
- **Essential cookies:** Required for platform functionality
- **Analytics cookies:** Help us understand usage patterns
- **Preference cookies:** Remember your settings

## Third-Party Services

Our platform may contain links to third-party websites or integrate with third-party services (e.g., payment processors). We are not responsible for the privacy practices of these third parties.

## Children's Privacy

Our platform is not intended for users under 18 years of age. We do not knowingly collect personal information from children.

## International Data Transfers

Your information may be transferred to and processed in countries other than Ghana. We ensure appropriate safeguards are in place for such transfers.

## Changes to This Policy

We may update this Privacy Policy from time to time. We will notify you of any changes by:
- Posting the new policy on this page
- Updating the "Last Updated" date
- Sending you an email notification for significant changes

## Data Retention

We retain your personal information for as long as necessary to:
- Provide our services to you
- Comply with legal obligations
- Resolve disputes
- Enforce our agreements

## Contact Us

If you have any questions about this Privacy Policy, please contact us:

- **Email:** alphalogiquetechnologies@gmail.com
- **Phone:** +233 (0)506534737 / +233 (0)3344991
- **Address:** Accra, Ghana

For data protection inquiries, you may also contact our Data Protection Officer at the email address above."""
    },

    'terms_of_service': {
        'title': 'Terms of Service',
        'slug': 'terms-of-service',
        'meta_description': 'Terms of Service for YEA Poultry Management System - Rules and guidelines for using our platform.',
        'meta_keywords': 'terms of service, terms and conditions, YEA PMS, user agreement, Ghana poultry',
        'excerpt': 'These Terms of Service govern your use of the YEA Poultry Management System platform.',
        'content': """## Agreement to Terms

These Terms of Service ("Terms") constitute a legally binding agreement made between you ("User," "you," or "your") and Alpha Logique Technologies ("Company," "we," "us," or "our") concerning your access to and use of the Youth Entrepreneurship in Agriculture (YEA) Poultry Management System (PMS) website and platform.

By accessing or using our platform, you agree to be bound by these Terms. If you disagree with any part of the terms, then you may not access the platform.

## Use of the Platform

### Eligibility
To use the YEA Poultry Management System, you must:
- Be at least 18 years of age
- Be a legal resident of Ghana or authorized to conduct business in Ghana
- Have the legal capacity to enter into a binding agreement
- Not be prohibited from using the platform under any applicable laws

### Account Registration
When you create an account with us, you must provide information that is accurate, complete, and current at all times. Failure to do so constitutes a breach of the Terms.

- You are responsible for safeguarding the password you use to access the platform
- You agree not to disclose your password to any third party
- You must notify us immediately upon becoming aware of any breach of security
- You are responsible for all activities that occur under your account

### Acceptable Use
You agree not to use the platform:
- In any way that violates any applicable national or international law
- To transmit any advertising or promotional material without our prior consent
- To impersonate or attempt to impersonate another user or person
- To engage in any conduct that restricts or inhibits anyone's use of the platform
- To introduce any viruses, malware, or other harmful material
- To attempt to gain unauthorized access to any portion of the platform

## YEA Program Terms

If you are participating in the Youth Entrepreneurship in Agriculture program:
- You agree to comply with all program requirements and guidelines
- You will provide accurate information in your application and ongoing reports
- You understand that program benefits are subject to availability and eligibility
- You agree to participate in required training and extension services
- You will maintain proper records of your farming activities
- You acknowledge that misrepresentation may result in program disqualification

## Marketplace Terms

### Sellers
If you use our marketplace as a seller, you agree to:
- Provide accurate descriptions of products and services
- Maintain adequate inventory to fulfill orders
- Ship products within the stated timeframe
- Respond promptly to buyer inquiries and complaints
- Comply with all applicable laws regarding product safety and labeling
- Honor the prices and terms listed in your product listings

### Buyers
If you use our marketplace as a buyer, you agree to:
- Pay for products you purchase in a timely manner
- Provide accurate shipping and contact information
- Accept delivery of products at the specified address
- Report any issues with orders within a reasonable timeframe
- Use products in accordance with their intended purpose

### Platform Fees
We may charge fees for certain services on the platform. These fees will be clearly disclosed before you incur them. We reserve the right to change our fee structure at any time with appropriate notice to users.

## Data Subscription Services

For institutional users accessing our data subscription services:
- Data is provided for lawful purposes only
- You may not resell or redistribute data without explicit permission
- API access is subject to rate limits and fair use policies
- Subscription fees are non-refundable unless otherwise specified
- We reserve the right to modify data access terms with notice

## Intellectual Property

The platform and its original content (excluding content provided by users), features, and functionality are and will remain the exclusive property of Alpha Logique Technologies and its licensors. The platform is protected by copyright, trademark, and other laws.

Our trademarks and trade dress may not be used in connection with any product or service without the prior written consent of Alpha Logique Technologies.

## User Content

Our platform may allow you to post, link, store, share and otherwise make available certain information, text, graphics, or other material ("User Content"). You are responsible for the User Content that you post on or through the platform.

By posting User Content, you grant us the right to use, modify, publicly perform, publicly display, reproduce, and distribute such content on and through the platform. You retain ownership of your User Content.

You represent and warrant that:
- You own or have the right to use the content you post
- Your content does not violate any third-party rights
- Your content is accurate and not misleading

## Limitation of Liability

In no event shall Alpha Logique Technologies, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential, or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from:
- Your access to or use of or inability to access or use the platform
- Any conduct or content of any third party on the platform
- Any content obtained from the platform
- Unauthorized access, use, or alteration of your transmissions or content

## Disclaimer

The platform is provided on an "AS IS" and "AS AVAILABLE" basis. Alpha Logique Technologies makes no warranties, expressed or implied, regarding the platform's operation or the information, content, or materials included thereon.

We do not warrant that:
- The platform will function uninterrupted, secure, or available at any particular time
- The results obtained from the platform will be accurate or reliable
- The quality of any products or services obtained through the platform will meet your expectations
- Any errors in the platform will be corrected

## Indemnification

You agree to defend, indemnify, and hold harmless Alpha Logique Technologies and its licensees, employees, contractors, agents, officers, and directors from any claims, damages, obligations, losses, liabilities, costs, or debt arising from:
- Your use of and access to the platform
- Your violation of any term of these Terms
- Your violation of any third-party right, including intellectual property rights
- Any claim that your User Content caused damage to a third party

## Termination

We may terminate or suspend your account immediately, without prior notice or liability, for any reason whatsoever, including without limitation if you breach the Terms.

Upon termination, your right to use the platform will immediately cease. If you wish to terminate your account, you may simply discontinue using the platform or contact us to request account deletion.

## Governing Law

These Terms shall be governed and construed in accordance with the laws of the Republic of Ghana, without regard to its conflict of law provisions.

Any disputes arising from these Terms shall be resolved in the courts of Ghana, and you consent to the exclusive jurisdiction of such courts.

## Changes to Terms

We reserve the right, at our sole discretion, to modify or replace these Terms at any time. We will provide notice of any changes by posting the new Terms on this page and updating the "Last Updated" date.

Your continued use of the platform after any changes constitutes acceptance of the new Terms. Please review these Terms periodically for changes.

## Severability

If any provision of these Terms is held to be unenforceable or invalid, such provision will be changed and interpreted to accomplish the objectives of such provision to the greatest extent possible under applicable law, and the remaining provisions will continue in full force and effect.

## Entire Agreement

These Terms constitute the entire agreement between you and Alpha Logique Technologies regarding our platform and supersede all prior agreements.

## Contact Us

If you have any questions about these Terms, please contact us:

- **Email:** alphalogiquetechnologies@gmail.com
- **Phone:** +233 (0)506534737 / +233 (0)3344991
- **Address:** Accra, Ghana"""
    },

    'faq': {
        'title': 'Frequently Asked Questions',
        'slug': 'faq',
        'meta_description': 'Frequently Asked Questions about the YEA Poultry Management System - Get help with registration, features, and support.',
        'meta_keywords': 'FAQ, frequently asked questions, help, YEA PMS, poultry farming Ghana, support',
        'excerpt': 'Find answers to commonly asked questions about the YEA Poultry Management System.',
        'content': """## Getting Started

### How do I register for the platform?
You can register by clicking the "Apply Now" button on the homepage and completing the Expression of Interest (EOI) application form. Once approved, you will receive login credentials to access the platform.

### What documents do I need to apply?
You will need:
- Valid Ghana Card
- Proof of address
- Farm location details
- Basic information about your poultry farming experience (if any)

### Is there a fee to join the program?
The basic registration is free. However, certain premium features and marketplace services may have associated fees which will be clearly disclosed.

### How long does the application process take?
Application review typically takes 5-10 business days. You can track your application status using the "Track Application" feature on our website.

---

## Platform Features

### What can I do on the platform?
The YEA PMS platform allows you to:
- Manage your poultry farm records (flocks, feed, production)
- Track health and mortality data
- Sell products through the marketplace
- Access training resources and extension services
- Connect with other farmers and buyers
- Generate reports and analytics for your farm

### How does the marketplace work?
The marketplace connects farmers with buyers. As a seller, you can list your products (eggs, live birds, processed meat). Buyers can browse, compare prices, and place orders directly through the platform. We handle order management and provide transaction records.

### Can I use the platform on my phone?
Yes! The platform is fully mobile-responsive and works on smartphones, tablets, and computers. We recommend using a modern browser like Chrome, Firefox, or Safari for the best experience.

### Is there a mobile app?
Currently, we offer a web-based platform that works on all devices. A dedicated mobile app is planned for future release.

---

## Account & Security

### I forgot my password. What should I do?
Click on "Forgot Password" on the login page and enter your registered email address. You will receive a password reset link via email. Follow the instructions to create a new password.

### How do I update my profile information?
Log in to your account, navigate to your profile settings (usually accessible from the top-right menu), and update your information. Some fields may require verification before changes take effect.

### Is my data secure?
Yes. We use industry-standard encryption and security measures to protect your data, including:
- SSL/TLS encryption for all data transmission
- Secure password hashing
- Regular security audits
- Access controls and authentication

See our [Privacy Policy](/privacy-policy) for more details.

### Can I have multiple accounts?
No. Each user should have only one account associated with their Ghana Card number. Creating multiple accounts may result in account suspension.

---

## Farm Management

### How do I add my farm to the platform?
After logging in, navigate to "Farm Management" and click "Add Farm." Enter your farm details including location, size, and facilities. You can add multiple farms if applicable.

### How do I record daily production?
Go to "Production Records" in your dashboard and click "Add Record." Enter the date, number of eggs collected, and any notes. Regular recording helps generate accurate analytics.

### Can I track multiple flocks?
Yes. The platform supports tracking multiple flocks. Each flock can have its own records for breed, age, health, mortality, and production.

### How do I record feed inventory?
Navigate to "Feed Management" to add feed purchases, track consumption, and monitor inventory levels. The system will alert you when stock is running low.

---

## Marketplace

### How do I list products for sale?
Go to "Marketplace" → "My Products" → "Add New Product." Enter product details, pricing, available quantity, and upload photos. Your listing will be visible to buyers once published.

### How do I receive payments?
Payments are processed through the platform. You can set up your preferred payment method (mobile money, bank transfer) in your profile settings. Funds are released according to our payment schedule.

### What are the marketplace fees?
We charge a small commission on successful sales to maintain the platform. Current fees are displayed when you list a product and are deducted automatically from your earnings.

### How do I handle disputes?
If you have an issue with an order, use the "Report Issue" button on the order details page. Our support team will mediate and help resolve the dispute fairly.

---

## Support

### How can I get help?
You can:
- Visit our [Contact page](/contact)
- Email us at alphalogiquetechnologies@gmail.com
- Call our support line: +233 (0)506534737
- Use the help feature within the platform

### Who are Extension Officers?
Extension Officers are trained professionals who provide on-farm support, training, and guidance to help you succeed in poultry farming. They can assist with:
- Best practices for poultry management
- Disease prevention and health management
- Record keeping and compliance
- Connecting with program resources

### How do I report a problem or bug?
Use the "Report Issue" feature in the app or contact our support team directly with:
- A description of the problem
- Steps to reproduce the issue
- Screenshots if possible
- Your device and browser information

### What are the platform's operating hours?
The platform is available 24/7. Our support team operates Monday-Friday, 8:00 AM - 5:00 PM GMT. Urgent issues can be reported anytime via email.

---

## Program Information

### What is the YEA Poultry Program?
The Youth Entrepreneurship in Agriculture (YEA) Poultry Program is a government initiative to support young Ghanaians in establishing sustainable poultry farming businesses. It provides training, resources, and market access.

### What support do program participants receive?
Participants may receive:
- Training on poultry management
- Access to extension officers
- Subsidized inputs (subject to availability)
- Market linkages through the platform
- Business development support

### How do I know if I'm eligible?
Eligibility requirements include:
- Ghanaian citizenship
- Age between 18-35 years
- Willingness to commit to poultry farming
- Basic literacy skills

Check the application form for complete eligibility criteria."""
    },

    'about_us': {
        'title': 'About YEA Poultry Management System',
        'slug': 'about-us',
        'meta_description': 'About the YEA Poultry Management System - A digital platform supporting Ghana\'s poultry farmers through the Youth Entrepreneurship in Agriculture program.',
        'meta_keywords': 'about YEA PMS, poultry management, Ghana agriculture, YEA poultry program, Alpha Logique',
        'excerpt': 'The YEA Poultry Management System is a comprehensive digital platform designed to support and empower poultry farmers across Ghana.',
        'content': """## Our Mission

The **YEA Poultry Management System (PMS)** is a comprehensive digital platform designed to support and empower poultry farmers across Ghana. Developed in partnership with the Youth Entrepreneurship in Agriculture (YEA) program, we aim to transform the poultry industry through technology, education, and market access.

## What We Do

### Farm Management
We provide farmers with digital tools to efficiently manage their poultry operations:
- Track flock health, growth, and mortality
- Monitor feed inventory and consumption
- Record daily egg production
- Generate insights and analytics

### Marketplace
Our integrated marketplace connects farmers directly with buyers:
- List and sell poultry products (eggs, live birds, processed meat)
- Access a wider customer base
- Manage orders and deliveries
- Track sales performance

### Training & Support
We support farmers with knowledge and guidance:
- Access to extension officers for on-farm support
- Educational resources and best practices
- Community of fellow farmers
- Program compliance assistance

## Our Impact

Since our launch, YEA PMS has:
- **10,000+** Registered farmers
- **500+** Active marketplace listings
- **16** Regions covered across Ghana
- **1,000+** Successful marketplace transactions

## Our Team

YEA PMS is developed and maintained by **Alpha Logique Technologies**, a Ghanaian technology company committed to building solutions that improve lives and livelihoods.

We work closely with:
- **Youth Entrepreneurship in Agriculture (YEA)** - Program administration
- **Ministry of Food and Agriculture** - Policy and guidance
- **Extension Officers** - On-ground farmer support
- **Financial Partners** - Payment processing and financial services

## Our Values

- **Empowerment:** Giving farmers the tools to succeed
- **Transparency:** Clear processes and fair dealings
- **Innovation:** Leveraging technology for agriculture
- **Community:** Building connections that strengthen the industry
- **Sustainability:** Supporting long-term agricultural development

## Contact Us

We'd love to hear from you!

- **Email:** alphalogiquetechnologies@gmail.com
- **Phone:** +233 (0)506534737 / +233 (0)3344991
- **Address:** Accra, Ghana

For technical support, visit our [Contact page](/contact-us) or check the [FAQ](/faq)."""
    },

    'contact_info': {
        'title': 'Contact Us',
        'slug': 'contact-us',
        'meta_description': 'Contact the YEA Poultry Management System support team - Email, phone, and address information.',
        'meta_keywords': 'contact, support, help, YEA PMS, customer service, Ghana',
        'excerpt': 'Get in touch with our support team for assistance.',
        'content': """## Get In Touch

We're here to help! Whether you have questions about the platform, need technical support, or want to learn more about the YEA program, our team is ready to assist you.

## Contact Information

### Email
**General Inquiries:** alphalogiquetechnologies@gmail.com

### Phone
**Support Line:** +233 (0)506534737  
**Alternative:** +233 (0)3344991

**Hours:** Monday - Friday, 8:00 AM - 5:00 PM GMT

### Office Address
Alpha Logique Technologies  
Accra, Ghana

## Support Options

### Technical Support
For issues with the platform, login problems, or bug reports:
- Email us with a description of the issue
- Include screenshots if possible
- Provide your registered email address

### Program Inquiries
For questions about the YEA program, eligibility, or applications:
- Check our [FAQ page](/faq) for common questions
- Contact your local YEA office
- Reach out to us via email

### Marketplace Support
For buyer/seller disputes, payment issues, or order problems:
- Use the "Report Issue" feature on your order
- Email us with your order number
- Our team will respond within 24-48 hours

## Feedback

We value your feedback! Help us improve the platform by sharing:
- Feature suggestions
- User experience feedback
- Success stories

Send your feedback to alphalogiquetechnologies@gmail.com with the subject "Feedback."

## Social Media

Follow us for updates and news:
- Facebook: [YEA PMS](#)
- Twitter: [YEA PMS](#)
- Instagram: [YEA PMS](#)"""
    }
}


class Command(BaseCommand):
    help = 'Seed required CMS pages (Privacy Policy, Terms of Service, FAQ, About Us, Contact) for AdSense compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate pages even if they already exist',
        )
        parser.add_argument(
            '--publish',
            action='store_true',
            default=True,
            help='Automatically publish pages (default: True)',
        )
        parser.add_argument(
            '--pages',
            nargs='+',
            choices=['privacy_policy', 'terms_of_service', 'about_us', 'faq', 'contact_info', 'all'],
            default=['all'],
            help='Specific pages to seed (default: all)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        force = options['force']
        publish = options['publish']
        pages_to_create = options['pages']
        dry_run = options.get('dry_run', False)
        
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=' * 60))
        self.stdout.write(self.style.HTTP_INFO('  YEA PMS - CMS Content Seeding'))
        self.stdout.write(self.style.HTTP_INFO('  AdSense Compliance Pages'))
        self.stdout.write(self.style.HTTP_INFO('=' * 60))
        self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            self.stdout.write('')
        
        if 'all' in pages_to_create:
            pages_to_create = list(LEGAL_PAGES.keys())
        
        # Try to get a super admin user for audit trail
        admin_user = User.objects.filter(role='SUPER_ADMIN', is_active=True).first()
        
        if admin_user:
            self.stdout.write(f'Using admin user: {admin_user.username}')
        else:
            self.stdout.write(self.style.WARNING('No SUPER_ADMIN found - pages will have no creator'))
        
        self.stdout.write('')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        # Priority order for AdSense compliance
        priority_order = ['privacy_policy', 'terms_of_service', 'faq', 'about_us', 'contact_info']
        pages_to_create_ordered = [p for p in priority_order if p in pages_to_create]
        
        for page_type in pages_to_create_ordered:
            if page_type not in LEGAL_PAGES:
                self.stdout.write(self.style.WARNING(f'Unknown page type: {page_type}'))
                continue
            
            page_data = LEGAL_PAGES[page_type]
            
            # Check if page already exists
            existing = ContentPage.objects.filter(page_type=page_type, is_deleted=False).first()
            
            if existing and not force:
                self.stdout.write(self.style.WARNING(
                    f'  ⏭️  {page_data["title"]} already exists (use --force to update)'
                ))
                skipped_count += 1
                continue
            
            if dry_run:
                if existing:
                    self.stdout.write(self.style.SUCCESS(
                        f'  📝 Would update: {page_data["title"]}'
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'  ➕ Would create: {page_data["title"]}'
                    ))
                continue
            
            if existing and force:
                # Update existing page
                existing.title = page_data['title']
                existing.slug = page_data['slug']
                existing.content = page_data['content'].strip()
                existing.excerpt = page_data['excerpt']
                existing.meta_description = page_data['meta_description']
                existing.meta_keywords = page_data['meta_keywords']
                existing.version += 1
                existing.updated_by = admin_user
                
                if publish:
                    existing.status = ContentPage.Status.PUBLISHED
                    existing.published_at = timezone.now()
                
                existing.save()
                
                # Create revision
                ContentPageRevision.objects.create(
                    page=existing,
                    version=existing.version,
                    title=existing.title,
                    content=existing.content,
                    excerpt=existing.excerpt,
                    changed_by=admin_user,
                    change_summary='Content updated via seed_legal_pages command (January 2026 revision)'
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Updated: {page_data["title"]} (v{existing.version})'
                ))
                updated_count += 1
            else:
                # Create new page
                page = ContentPage.objects.create(
                    page_type=page_type,
                    title=page_data['title'],
                    slug=page_data['slug'],
                    content=page_data['content'].strip(),
                    excerpt=page_data['excerpt'],
                    meta_description=page_data['meta_description'],
                    meta_keywords=page_data['meta_keywords'],
                    status=ContentPage.Status.PUBLISHED if publish else ContentPage.Status.DRAFT,
                    published_at=timezone.now() if publish else None,
                    version=1,
                    created_by=admin_user,
                    updated_by=admin_user,
                )
                
                # Create initial revision
                ContentPageRevision.objects.create(
                    page=page,
                    version=1,
                    title=page.title,
                    content=page.content,
                    excerpt=page.excerpt,
                    changed_by=admin_user,
                    change_summary='Initial version created via seed_legal_pages command'
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Created: {page_data["title"]}'
                ))
                created_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  Seeding Complete!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(f'  📊 Results:')
        self.stdout.write(f'      Created: {created_count}')
        self.stdout.write(f'      Updated: {updated_count}')
        self.stdout.write(f'      Skipped: {skipped_count}')
        self.stdout.write('')
        
        if not dry_run and (created_count > 0 or updated_count > 0):
            if publish:
                self.stdout.write(self.style.SUCCESS('  🌐 Public endpoints now available:'))
                self.stdout.write('')
                self.stdout.write('  AdSense Required (High Priority):')
                self.stdout.write('    • /api/public/cms/privacy-policy/')
                self.stdout.write('    • /api/public/cms/terms-of-service/')
                self.stdout.write('')
                self.stdout.write('  Additional Pages (Medium Priority):')
                self.stdout.write('    • /api/public/cms/pages/faq/')
                self.stdout.write('    • /api/public/cms/pages/about-us/')
                self.stdout.write('    • /api/public/cms/pages/contact/')
            else:
                self.stdout.write(self.style.WARNING(
                    '  ⚠️  Pages created as drafts. Use the admin panel to publish them.'
                ))
        
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('  Tip: Use --force to update existing pages'))
        self.stdout.write(self.style.HTTP_INFO('  Tip: Admin can edit pages at /admin/cms'))
        self.stdout.write('')
