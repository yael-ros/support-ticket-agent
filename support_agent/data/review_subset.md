# Gold set hand-review sheet (40 tickets)

For each ticket below, read the subject/body and decide whether the weak
label (taken from the dataset's own `queue`/`priority` fields) is
correct.

- Change REVIEWED from "no" to "yes" once you've made a decision on that ticket — this is what tells apply_review.py you actually looked at it, since blank correction fields alone can't distinguish "confirmed correct" from "haven't gotten to this one yet". Rows still marked "no" are skipped and reported, not guessed at.
- If the weak label is correct: leave CORRECTED_CATEGORY / CORRECTED_URGENCY blank.
- If it's wrong: write the correct value on that line.
- NOTES is optional — use it for anything worth flagging (ambiguous ticket, borderline urgency, etc).

Valid categories: technical_support, product_support, customer_service, it_support, billing_and_payments, returns_and_exchanges, service_outages_and_maintenance, sales_and_pre_sales, human_resources, general_inquiry
Valid urgencies: low, medium, high, critical

Do not remove or edit the "### ticket-XXXXXX" lines — apply_review.py matches rows by that exact id. When you're done, save this file and ask Claude to run `python -m support_agent.data.apply_review`.

---

### ticket-023619

Subject: Updates for Digital Marketing Tools

Body:

Please update the digital marketing tools to enhance brand growth and the effectiveness of strategy implementation

Weak label: category=customer_service, urgency=low

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: Feature/update request for marketing tools

### ticket-022168

Subject: Investment Optimization Software Projection Inaccuracy

Body:

The investment optimization software is producing inaccurate projections. Recent updates and data inputs might be causing these errors. Despite resetting the system and reviewing data inputs, the discrepancies still exist. Assistance is needed to resolve this issue.

Weak label: category=product_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: technical_support

CORRECTED_URGENCY: medium

NOTES: Software calculation bug after update

### ticket-005861

Subject: Problems with Healthcare Data Accessibility

Body:

A healthcare organization faced delays in accessing data. Despite updating the firewall and antivirus software, the problem remains unresolved. We require support to troubleshoot and fix the issue promptly. Kindly assist us in identifying the root cause and suggest solutions to ensure quick access to essential patient information.

Weak label: category=customer_service, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: technical_support

CORRECTED_URGENCY: high

NOTES: Patient data access block in healthcare setting

### ticket-010321

Subject: Problem with Investment Analytics Tools

Body:

The financial firm's investment analytics tools are not functioning correctly, leading to data discrepancies in reports. It's possible that recent software updates have caused compatibility issues. The team has tried to resolve the issue by rebooting systems and reinstalling affected applications, but the problem still persists.

Weak label: category=technical_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: 

CORRECTED_URGENCY: 

NOTES: Verified technical issue with high impact

### ticket-006070

Subject: Enhancing Digital Brand Growth Strategies

Body:

Is it possible to gain insights on optimizing digital strategies?

Weak label: category=technical_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: sales_and_pre_sales

CORRECTED_URGENCY: low

NOTES: General advisory inquiry, not tech bug or high priority

### ticket-013462

Subject: (no subject)

Body:

Is it possible to get information on integrating Keras Docker for investment analytics? Thank you.

Weak label: category=customer_service, urgency=low

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: General technical guidance request

### ticket-021866

Subject: Issues Detected with Windows 10 Pro Data Synchronization

Body:

The project timelines are failing to synchronize. This could be due to conflicting software updates or a damaged database. Steps already taken include restarting the system, applying updates, and cleaning the cache, yet the issue remains unresolved.

Weak label: category=product_support, urgency=low

REVIEWED: yes

CORRECTED_CATEGORY: technical_support

CORRECTED_URGENCY: medium

NOTES: Database/sync issue preventing workflow

### ticket-009773

Subject: Investigation into Variance of Projected Investment Returns

Body:

Detected a discrepancy in the projected investment returns within the analytics report, which may be due to data integration errors. The source data has been validated and the analytical models have been recalibrated.

Weak label: category=returns_and_exchanges, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: technical_support

CORRECTED_URGENCY: medium

NOTES: Incorrectly categorized as physical returns

### ticket-002254

Subject: Today's Delays in Project Dashboard Loading

Body:

Users reported intermittent delays when loading the project dashboard, potentially due to a higher number of concurrent users. Restarting the servers and clearing the cache did not resolve the problem. The issue remains unresolved and requires prompt assistance to minimize disruptions.

Weak label: category=technical_support, urgency=low

REVIEWED: yes

CORRECTED_CATEGORY: technical_support

CORRECTED_URGENCY: high

NOTES: High user impact/performance bottleneck

### ticket-013296

Subject: Improvements for Digital Marketing Tools and Strategies

Body:

Customer Support, I am writing to request enhancements to the digital marketing tools and strategies currently used to drive brand growth and engagement across our products. While I believe the current tools and strategies are effective, I think there is room for improvement to increase brand visibility and customer interaction. Specifically, I would like to see the implementation of personalized marketing campaigns, improved social media management, and enhanced data analytics to better track customer behavior and preferences. Additionally, I think it would be beneficial to explore new

Weak label: category=technical_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: Feature request, not a high urgency bug

### ticket-018663

Subject: Problem with Software Stopping

Body:

The software has experienced multiple stops. There might be a fitting issue or a corrupted update.

Weak label: category=product_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: technical_support

CORRECTED_URGENCY: high

NOTES: Software crashes causing outage

### ticket-021503

Subject: Performance Problem with SQL Server 2019

Body:

We are facing performance challenges with SQL Server 2019, which are leading to delays in marketing analytics. This could be due to high data traffic or configuration errors. We have already tried database optimization and restarting the server, but the issues still persist. We need your help to resolve this issue as soon as possible.

Weak label: category=technical_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: 

CORRECTED_URGENCY: high

NOTES: DB performance impact on marketing analytics

### ticket-017132

Subject: Request for Information on Securing Medical Data in Hospital IT Systems

Body:

We value your interest in our services for securing medical data within hospital IT systems. Our team offers a variety of solutions to ensure the confidentiality and integrity of sensitive medical information. We provide security assessments, data encryption, and compliance consulting to meet regulatory requirements. Please provide details on your current infrastructure and the type of medical data you are working with, so we can discuss your specific needs. We would like to schedule a call for your convenience.

Weak label: category=sales_and_pre_sales, urgency=low

REVIEWED: yes

CORRECTED_CATEGORY: 

CORRECTED_URGENCY: 

NOTES: Pre-sales inquiry verified

### ticket-005062

Subject: Guidance on Securing Patient Information

Body:

Drafting a request for best practices to safeguard patient data utilizing Firebase and Kaspersky Internet Security. Could you provide details on how to implement strong security protocols to protect sensitive patient records? I would be grateful for any suggestions or resources that can help ensure the confidentiality, integrity, and availability of patient information.

Weak label: category=it_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: medium

NOTES: Security best practices guidance request

### ticket-015358

Subject: Problem with JIRA Integration API

Body:

Facing occasional disruptions in JIRA and Bitbucket integration because of API problems.

Weak label: category=product_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: technical_support

CORRECTED_URGENCY: medium

NOTES: API integration bug

### ticket-012947

Subject: Reported Issue of Unauthorized Access to Medical Data

Body:

Facing unauthorized access attempts to medical data. This might have occurred due to weak access control vulnerabilities in the system. So far, we have reviewed user permissions and updated firewall settings. We kindly request your assistance in investigating the matter and providing recommendations to enhance the system's security. Please let us know the next steps to resolve this issue.

Weak label: category=customer_service, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: it_support

CORRECTED_URGENCY: high

NOTES: Security vulnerability and unauthorized access attempt

### ticket-008262

Subject: Request for Enhancement of Digital Marketing Strategies to Boost Brand Visibility and Engagement

Body:

Dear Customer Support, I am writing to request an enhancement in our digital marketing strategies to boost the visibility and engagement of our brand, particularly for the affected products. I would like to involve social media campaigns and targeted advertisements to reach a wider audience and increase sales.

Weak label: category=sales_and_pre_sales, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: General growth enhancement request

### ticket-020382

Subject: Software Crash Concern

Body:

I'm contacting to report recurring software crashes and errors that started recently. The problem may stem from incompatible updates or conflicts between different products. Despite restarting and reinstalling the affected software, which mitigated the issue temporarily, it still recurs, necessitating additional support. Could you please assist in troubleshooting or offer a solution to prevent these crashes and errors from happening again?

Weak label: category=technical_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: 

CORRECTED_URGENCY: 

NOTES: Recurring software crash verified

### ticket-004434

Subject: (no subject)

Body:

Customer Support, I am reaching out to inquire about implementing advanced data analytics tools to optimize investment strategies and improve portfolio performance analysis. These tools would enable our team to make data-driven decisions, identify emerging trends, and seize new opportunities. They would offer real-time insights, predictive analytics, and risk assessments. I would appreciate guidance on the available options for integrating these tools with our existing systems. Please let me know how your team can assist us.

Weak label: category=returns_and_exchanges, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: Feature inquiry misclassified as returns

### ticket-005376

Subject: Digital Strategy Failures Occurring Unexpectedly

Body:

The digital strategies implemented by the marketing agency are not successfully promoting brand expansion as anticipated. Potential reasons may involve technical issues or ineffective approaches. Efforts to resolve the problem have included reviewing the strategy and performing basic troubleshooting, but the outcomes have not improved.

Weak label: category=it_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: customer_service

CORRECTED_URGENCY: medium

NOTES: Non-technical strategy execution issue

### ticket-018662

Subject: Docker Support

Body:

Can you provide information on using Docker for data analytics in financial investment optimization? I would like to learn more about it.

Weak label: category=billing_and_payments, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: General guidance query misclassified as billing

### ticket-005207

Subject: (no subject)

Body:

Customer Support reports a critical issue impacting the hospital's systems. The hospital has experienced multiple data breaches, likely due to outdated security patches on several products. The team has attempted to resolve the problem by applying patch updates, performing malware scans, and conducting access audits. Despite these efforts, the breaches have not been fully contained. The breaches have compromised sensitive patient information, raising serious concerns about potential repercussions. Immediate assistance is required to identify the root cause.

Weak label: category=product_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: it_support

CORRECTED_URGENCY: high

NOTES: Active data breach in hospital environment

### ticket-005003

Subject: Request for Assistance with Data Security Breach

Body:

Recently, we identified a possible data breach due to unusual network activity. Our investigation indicates that outdated firewall configurations may have played a role in this incident. We promptly updated the firewall and ran a comprehensive system scan; however, the problem persists. We are worried about the potential exposure of sensitive patient information and seek your help to resolve this issue promptly. Could you please advise on the appropriate next steps to secure our network and safeguard sensitive data?

Weak label: category=technical_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: it_support

CORRECTED_URGENCY: high

NOTES: Security incident investigation

### ticket-011154

Subject: (no subject)

Body:

Dear Customer Support, I am seeking guidance on integrating IBM SPSS Statistics 28 with Scikit-learn for investment analysis. I am exploring different tools and data analysis methods, and believe that combining these two powerful libraries could significantly enhance my investment analysis capabilities. However, I am unsure about the best approach to integrate them. Could you provide some guidance and resources to get started? I would appreciate information on compatible versions, required dependencies, and examples.

Weak label: category=technical_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: Integration advice inquiry

### ticket-018103

Subject: Project Pricing Plans

Body:

Inquiring about the pricing plans and billing options for the project management SaaS service. Could you provide details on the different tiers and their respective features? It would be helpful if you could clarify the available billing options, such as monthly and yearly subscriptions, and any discounts for long-term commitments. Additionally, are there any additional costs associated with support and implementation? I am looking to get a better understanding of the total cost of ownership for the platform.

Weak label: category=billing_and_payments, urgency=low

REVIEWED: yes

CORRECTED_CATEGORY: 

CORRECTED_URGENCY: 

NOTES: Verified billing/pricing query

### ticket-002660

Subject: Revise Digital Marketing Initiatives

Body:

Requesting an update on digital marketing strategies aimed at boosting brand development, with a focus on products such as the Smart-Medizinspender Barcode-Scanner. Believing this will help improve online visibility and sales.

Weak label: category=returns_and_exchanges, urgency=low

REVIEWED: yes

CORRECTED_CATEGORY: customer_service

CORRECTED_URGENCY: low

NOTES: Misclassified as returns

### ticket-017187

Subject: Imprecise Investment Projections Noted

Body:

Issue: Sudden inaccuracy in investment projections. Reason: Possible data feed disruption. Attempted: Already restarted the analytics engine.

Weak label: category=product_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: technical_support

CORRECTED_URGENCY: medium

NOTES: Calculation inaccuracy due to data feed issue

### ticket-010151

Subject: Seek Assistance for Integration Support

Body:

Dear support team, I am writing to request support for integrating our SaaS platform with various affected products. This integration aims to improve project management functionality and enhance workflow compatibility. I would greatly appreciate any guidance on the necessary steps to achieve this integration. Please let me know if there are any additional requirements or information you need from my end. I look forward to hearing from you soon.

Weak label: category=technical_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: medium

NOTES: SaaS integration support request

### ticket-002566

Subject: Ensuring Security of Medical Data

Body:

Customer Support, I am contacting you to request comprehensive guidance on securing medical data within hospital infrastructure using appropriate solutions. Could you share information on best practices and protocols for safeguarding sensitive patient information? I would also appreciate recommendations on implementing strong security measures to prevent data breaches and cyber threats. Furthermore, please provide details on compliance requirements and regulations that need to be adhered to. Thank you for your time and assistance. I look forward to your prompt response.

Weak label: category=product_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: it_support

CORRECTED_URGENCY: low

NOTES: Compliance and best practices inquiry

### ticket-004613

Subject: Safeguarding Medical Data in Healthcare Facilities

Body:

Customer Support, I am seeking guidance on how to secure medical data utilizing Mesh-Netzwerk Simulink hospital systems. As you may be aware, protecting sensitive patient information is of critical importance in the healthcare industry. I am interested in learning about the tools and methods used to ensure the confidentiality, integrity, and availability of medical data. Could you please provide recommendations and best practices for implementing Mesh-Netzwerk Simulink in a hospital environment? I would appreciate any relevant documentation or resources you can share on this topic.

Weak label: category=technical_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: General guidance request, lowered urgency from high

### ticket-002922

Subject: Request for Assistance in Enhancing Investment Strategies

Body:

Dear Customer Support, I am reaching out to inquire about the analytics tools available for optimizing investment strategies within financial firms. Could you please provide detailed information on the types of tools offered, tailored to meet specific organizational needs? I would also appreciate guidance on selecting the most appropriate tools and implementing them effectively. Furthermore, I am interested in understanding the benefits of utilizing analytics tools for investment strategies, such as improved portfolio performance and enhanced risk management. Kindly let me know the next steps.

Weak label: category=technical_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: sales_and_pre_sales

CORRECTED_URGENCY: low

NOTES: Product inquiry and selection assistance

### ticket-008950

Subject: Unapproved Entry into Medical Files

Body:

There was an unauthorized access to medical data within the hospital's IT systems. Efforts to address the issue involved changing passwords and enhancing security measures.

Weak label: category=billing_and_payments, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: it_support

CORRECTED_URGENCY: high

NOTES: Severe security/unauthorized access issue misclassified as billing

### ticket-010478

Subject: Concerns Regarding Performance of Data Analytics Tool

Body:

The data analytics tool experienced a crash during peak usage hours, which disrupted our investment optimization processes. This issue may have arisen due to server overload following a recent software update. After restarting the tool and monitoring server performance, along with clearing the cache, the issues still persist. I would greatly appreciate it if you could look into this matter and provide a solution at the earliest possible time. Please let me know if there is any additional information needed to resolve this issue.

Weak label: category=technical_support, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: 

CORRECTED_URGENCY: 

NOTES: Verified technical support bug with high severity

### ticket-021713

Subject: Enhancing Security for Medical Data Solutions

Body:

Seeking advice on securing medical data solutions for our hospital. Could you offer information on security measures that can protect sensitive patient information? Your guidance and resources would be greatly appreciated to ensure the confidentiality and integrity of our medical data. Thank you for your assistance.

Weak label: category=billing_and_payments, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: Advisory request misclassified as billing

### ticket-002968

Subject: Assist with Digital Product Promotion

Body:

I am seeking information on digital strategies used to promote technological products such as digital cameras and IBM Cloud services. Could you share detailed methods and techniques employed to enhance brand visibility and boost sales? Such information would be valuable for understanding how to effectively market comparable products. I look forward to your insights on this matter. Your guidance would be highly appreciated.

Weak label: category=customer_service, urgency=low

REVIEWED: yes

CORRECTED_CATEGORY: 

CORRECTED_URGENCY: 

NOTES: Verified low urgency query

### ticket-020573

Subject: Data Leak Issue

Body:

Unanticipated data leaks have been observed. It is possible that inadequate access controls are the reason. Restarting Redis 6.2 was attempted, but the problem continues. Additional support is required to address this.

Weak label: category=it_support, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: it_support

CORRECTED_URGENCY: high

NOTES: Active data leak elevated to high urgency

### ticket-013478

Subject: Safe Medical Information

Body:

Offer details on securing medical information

Weak label: category=customer_service, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: low

NOTES: Vague informational request, lowered urgency

### ticket-006849

Subject: Support for Integrating Elasticsearch

Body:

inquiring about the process of integrating Elasticsearch into our project management SaaS. Would greatly appreciate any information or resources that could guide us in getting started. Thank you for your assistance, and I look forward to hearing back from you soon.

Weak label: category=product_support, urgency=low

REVIEWED: yes

CORRECTED_CATEGORY: 

CORRECTED_URGENCY: 

NOTES: Verified product guidance query

### ticket-002215

Subject: Access Issues Due to Healthcare Outages

Body:

Healthcare providers faced outages affecting Zoom, WLAN routers, and PHP 8.0, which disrupted access to medical data. The initial measures taken included rebooting systems and applying patch updates, but these did not resolve the problem.

Weak label: category=service_outages_and_maintenance, urgency=high

REVIEWED: yes

CORRECTED_CATEGORY: 

CORRECTED_URGENCY: 

NOTES: Verified outage issue

### ticket-003823

Subject: Cloud-Based Project Management Solution

Body:

Our client requires detailed guidance on integrating and setting up the scalable SaaS project management platform. Could you supply comprehensive step-by-step tutorials to assist with initial setup? Additional documentation explaining features and functionalities would be highly beneficial to maximize the software's potential. Your prompt support is appreciated. We look forward to your response soon.

Weak label: category=customer_service, urgency=medium

REVIEWED: yes

CORRECTED_CATEGORY: product_support

CORRECTED_URGENCY: medium

NOTES: Setup and onboarding guidance