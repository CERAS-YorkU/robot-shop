# Practical Root Cause Localization for Microservice Systems via Trace Analysis

**Authors:**  
Zeyan Li\*,¶, Junjie Chen†, Rui Jiao\*,¶, Nengwen Zhao\*,¶, Zhijun Wang‡, Shuwei Zhang‡, Yanjun Wu‡, Long Jiang‡, Leiqin Yan‡, Zikai Wang§, Zhekang Chen§, Wenchi Zhang§, Xiaohui Nie\*,¶, Kaixin Sui§, Dan Pei\*,¶  
\*Tsinghua University  
†College of Intelligence and Computing, Tianjin University  
‡China Minsheng Bank  
§BizSeer  
¶Beijing National Research Center for Information Science and Technology (BNRist)  

***

## Abstract

Microservice architecture is applied by an increasing number of systems because of its benefits on delivery, scalability, and autonomy. It is essential but challenging to localize root-cause microservices promptly when a fault occurs. Traces are helpful for root-cause microservice localization, and thus many recent approaches utilize them. However, these approaches are less practical due to relying on supervision or other unrealistic assumptions. To overcome their limitations, a more practical root-cause microservice localization approach named **TraceRCA** is proposed. The key insight of TraceRCA is that a microservice with more abnormal and less normal traces passing through it is more likely to be the root cause. Based on it, TraceRCA is composed of trace anomaly detection, suspicious microservice set mining and microservice ranking. Experiments are conducted on hundreds of injected faults in a widely-used open-source microservice benchmark and a production system. The results show that TraceRCA is effective in various situations. The top-1 accuracy of TraceRCA outperforms state-of-the-art unsupervised approaches by 44.8%. Besides, TraceRCA is applied in a large commercial bank, and it helps operators localize root causes for real-world faults accurately and efficiently. Several lessons learned from real-world deployment are also shared.

***

## I. Introduction

Microservice architecture is the latest trend in software service and is used by an increasing number of systems due to its faster delivery, better scalability, and greater autonomy. A modern microservice system consists of dozens to thousands of microservices deployed on hundreds to thousands of servers. Although extensive efforts have been devoted to quality assurance, microservice systems are typically fragile due to their large scale and complexity. Moreover, microservice system faults could cause enormous economic loss and damage user satisfaction. For example, the loss of one-hour downtime for Amazon.com on Prime Day in 2018 (its biggest sale event of the year) is up to 100 million USD. Therefore, once a fault happens for microservice systems, the urgent demand is to localize and mitigate it as soon as possible.

Over the years, many approaches have been proposed in the field, including invocation-based and trace-based approaches. The invocation-based approaches assume that the adjacent microservices with abnormal invocations are more likely to be the root causes. However, due to the complex dependencies and fault propagation among microservices, the anomaly invocations between adjacent microservices are not sufficient to reflect the locations of root causes.

The trace-based approaches overcome the above limitation by correlating all the microservices involved in a trace instead of just the adjacent ones. Here, all the invocations realizing the same user request form a trace. However, the existing trace-based approaches (MicroScope, TraceAnomaly, and MEPFL) still suffer from some practical issues.

- MicroScope uses directed acyclic graphs to represent dependency among microservices, but in practice, there often exist dependency cycles.
- TraceAnomaly focuses on detecting structural or latency anomalies of traces but ignores other metrics. Both TraceAnomaly and MicroScope localize root-cause microservices by assuming a fixed anomaly propagation pattern.
- MEPFL trains a supervised machine learning model to predict the root-cause microservices with a training corpus built by fault injection, whose effectiveness heavily depends on high coverage of all fault types, which is impractical.

Therefore, a more practical and better root-cause microservice localization approach is still required.

In this paper, a practical trace-based root-cause microservice localization approach called **TraceRCA** is proposed. The insight of TraceRCA is that a microservice with more abnormal traces and fewer normal traces passing through it is more likely to be the root-cause microservice. Similar insights are widely and successfully used in other domains such as spectrum-based program debugging and multi-dimensional root cause localization. This insight is also directly validated in microservice systems.

To apply the insight into root-cause microservice localization:

1. Abnormal traces are first detected.  
   TraceRCA infers trace normality based on its member invocations’ normality, which is detected by a designed unsupervised multi-metric anomaly detection method. Since not all metrics are related to the concerned fault and irrelevant anomalies could exist in any metrics, useful metrics are adaptively selected by testing whether each metric’s underlying distribution changes after the fault.

2. The second stage is to mine suspicious root-cause microservice sets satisfying the insight.  
   Mining suspicious microservice sets rather than microservices makes TraceRCA more practical because some faults only affect traces that pass through a specific set of microservices.

3. Finally, TraceRCA calculates a suspicious score for each microservice in the mined suspicious microservice sets.  
   Based on the number of traces containing incoming and outgoing abnormal invocations, TraceRCA dynamically infers the anomaly propagation pattern for calculating suspicious scores rather than assuming a fixed one. Microservices are then ranked so that operators can mitigate faults earlier.

An extensive study is conducted to evaluate TraceRCA based on:

- A popular open-source microservice benchmark (Train-Ticket)
- An Internet service provider’s production microservice system

Train-Ticket is one of the most extensive open-source microservice benchmarks. A total of 222 faults of 10 different categories are used. This is, to the authors’ knowledge, the most large-scale study in the field with respect to the number of faults, fault types, and benchmark scale. The experimental results show that TraceRCA ranks the root-cause microservices at top-1 in 83% of all faults and significantly outperforms state-of-the-art unsupervised approaches by 44.8%. TraceRCA is also applied to a large service-oriented production system in a large commercial bank, and lessons learned from this deployment are shared.

**Main contributions:**

- A novel unsupervised and lightweight root-cause microservice localization approach via trace analysis, based on a straightforward and simple insight.
- An unsupervised multi-metric trace anomaly detection method, which adaptively selects useful features for each fault and conducts invocation anomaly detection and trace anomaly inference based on the selected features.
- The most large-scale experimental study based on 2 benchmarks with 222 faults in 10 categories, demonstrating the effectiveness and efficiency of TraceRCA, along with lessons learned from deployment in a large production system.

***

## II. Basic Concepts

This section introduces some basic concepts. Their relationships are shown in Fig. 1 (described textually here).

- **Microservice system:** A system structured with microservice architecture.
- **Microservice architecture:** Architecture style that organizes a system as many lightweight, loosely-coupled, and independently-deployed services, called microservices. For example, Train-Ticket is organized as many microservices such as UI, seat, train, station, order, and price.

Each microservice has one or more **instances** (containers) hosted on **nodes** (physical or virtual machines). Each node can host many containers and microservices, and each microservice can also be hosted on different nodes.

When a microservice system realizes a user request, microservices invoke each other with specific application programming interfaces (APIs). A microservice can contain tens to hundreds of APIs.

- An **invocation (span)** belongs to a specific microservice caller→callee pair, referred to as a **microservice pair**.
- All invocations realizing the same user request form a **trace**.

Industrial microservice systems commonly use distributed tracing systems, which track execution of a request across services (traces). For example, when the button **Buy** is clicked in Train-Ticket, a user request is sent to buy a ticket:

- Microservice UI makes an API call to microservice verification.  
  This API call is an invocation belonging to microservice pair `UI→verification`. Each click triggers such an invocation; many invocations can exist for one pair.
- UI then calls other microservices (e.g., payment), triggering many other invocations.  
  All the invocations triggered by one click on **Buy**, which realize the same user request, form a trace.

**Fig. 1 (textual):** Relationship of concepts  
- User Request → Trace → Invocations (Spans)  
- Invocations are between Microservice Pairs  
- Microservices run in Instances (Containers) on Nodes within a Microservice System.

***

## III. Approach

TraceRCA contains three stages:

1. Trace anomaly detection  
2. Suspicious microservice set mining  
3. Microservice ranking  

By analyzing many real faults and summarizing manual diagnosis processes, the key insight is obtained: **a microservice with more abnormal traces and fewer normal traces passing through it is more likely to be the root cause.**

This insight:

- Is simple and effective.
- Holds in various situations, including partly faulty microservices (e.g., only one container is faulty) and multi-root-cause faults (validated in experiments).
- Can also be applied in similar architectures like service-oriented architectures.

Fig. 2 (textual) shows an overview: there are 5 traces, red dotted arcs represent abnormal invocations. The microservice set `{SA, SB}` is mined as the most suspicious set. Microservices are ranked based on suspicious scores.

### A. Trace Anomaly Detection

TraceRCA first designs a multi-metric invocation anomaly detection method to obtain normality of each invocation, then infers trace normality according to member invocations’ normality.

Traces are variable-length, so detecting anomalies directly on traces either leads to low efficiency or low accuracy when transforming them to fixed-length vectors. Therefore:

1. Detect abnormal invocations.
2. Infer abnormal traces based on these invocations.

The anomaly detection method is **unsupervised** to avoid limitations of supervised approaches and improve practicality.

#### 1) Multi-Metric Invocation Anomaly Detection

In a microservice system, there are various metrics (features). For example, in Train-Ticket:

- Latency and HTTP status of each invocation
- CPU usage, memory usage, network receive/send throughput, disk read/write throughput of each microservice

When a fault occurs, not all features are affected by the concerned fault. Due to wrong user inputs or random fluctuation, anomalies of irrelevant features may appear and become noise for anomaly detection, harming accuracy.

The method has two steps:

1. **Adaptively selecting useful features for each fault.**  
2. **Detecting abnormal invocations based on selected features.**

Fig. 3 (textual) shows the overview:

- Compute mean and standard deviation from historical invocations.
- Compute anomaly severity α.
- Select useful features by comparing distributions before and after fault.
- Detect abnormal invocations using a threshold on anomaly severity.

For a feature of a specific microservice pair (denoted as \(f\)):

- Use mean \(\mu_f\) and standard deviation \(\sigma_f\) of historical invocations to model normal state.
- For an invocation with feature value \(v_f\), anomaly severity is:

\[
\alpha = \frac{|v_f - \mu_f|}{\sigma_f}
\]

The larger \(\alpha\), the more likely it is abnormal.

To ensure robust and efficient calculation:

- Historical data for \(\mu_f\) and \(\sigma_f\) are:
  - Last-slot data (invocations in the last time slot before fault)
  - Last-period data (same slot of previous period, e.g., previous day)
- This combination captures both recent normal behavior and periodic patterns.
- Historical invocations during known previous faulty durations are excluded to eliminate bias.
- \(\mu_f\) and \(\sigma_f\) are maintained online and updated periodically (e.g., per minute).

**Feature usefulness:**  
If a feature is related to the concerned fault, more abnormal invocations (large \(\alpha\)) should appear after the fault.  

Let:

- \(\alpha_{\text{after}}\): average anomaly severity after fault  
- \(\alpha_{\text{before}}\): average anomaly severity of historical invocations  

A feature is considered useful if:

\[
\alpha_{\text{after}} - \alpha_{\text{before}} > \delta_{fs} \cdot \alpha_{\text{before}}
\]

Default \(\delta_{fs} = 10\%\).

**Abnormal invocations:**  
Based on selected useful features:

- An invocation is abnormal if it is abnormal with respect to any useful feature.
- An invocation is abnormal for a feature if its anomaly severity satisfies \(\alpha > \delta_{ad}\).  
  Default \(\delta_{ad} = 1\).

#### 2) Trace Anomaly Inference

Based on detected abnormal invocations, trace normality is inferred:

- A trace is abnormal if at least one member invocation is abnormal.
- This method takes as many abnormal traces as possible into consideration, making TraceRCA robust and efficient.

### B. Suspicious Root-Cause Microservice Set Mining

After trace anomaly detection, suspicious microservice sets satisfying the insight are mined, rather than individual microservices.

Motivation:

- In practice, sometimes only traces passing through a specific microservice set are affected by a fault.
- Example: A buggy API in microservice S1 is triggered only by invocations from S2, but many other microservices also invoke S1. Fractions of abnormal traces passing through only S1 or only S2 would be small, but those passing through both would be large.

TraceRCA does not mine microservice sequences or subgraphs because:

- The goal is to localize root-cause microservices.
- Sequences or subgraphs are redundant for this purpose and harm efficiency.

Two key metrics are proposed to evaluate how a microservice set satisfies the insight:

- **Support** \(P(X|Y)\):  
  - \(X\): set of traces passing through all microservices in the set  
  - \(Y\): set of all abnormal traces  
  - \(P(X|Y)\): percentage of abnormal traces that pass through all microservices in the set
- **Confidence** \(P(Y|X)\):  
  - percentage of abnormal traces among all traces passing through all microservices in the set

A microservice set is likely a root-cause set if it has both high \(P(X|Y)\) and high \(P(Y|X)\). Empirical validation via kernel density estimation shows root-cause sets cluster at high values of both metrics.

However, the number of potential microservice sets is exponential in the number of microservices. To reduce search space:

1. **Frequent pattern mining (FP-Growth):**  
   - Identify microservice sets with high support \(P(X|Y)\).  
   - A microservice set is frequent if its support exceeds threshold \(\delta_{spt}\).  
   - Example (Fig. 2 textual): abnormal traces: `{SA, SB, SD, SE}`, `{SA, SB, SC, SD}`, `{SA, SB, SC, SE}`; the most frequent set is `{SA, SB}` with support 1.  
   - Default \(\delta_{spt} = 10\%\).

2. **Jaccard Index (JI) as unified metric:**  
   - JI measures similarity between:
     - \(X\): traces containing the microservice set  
     - \(Y\): abnormal traces  
   - Defined as:

\[
\text{JI} = \frac{P(X \cap Y)}{P(X \cup Y)}
\]

   - JI is a monotonically increasing function of harmonic mean of \(P(X|Y)\) and \(P(Y|X)\).  
   - Microservice sets are sorted by JI in descending order, and top-k sets are taken (default \(k=100\)).

### C. Microservice Ranking

Although suspicious microservice sets are available, operators need to investigate microservices one by one. A suspicious score for each microservice is therefore calculated.

The suspicious score combines:

- JI score of each suspicious set
- In-set suspicious score of each microservice within each suspicious set

**In-set suspicious score (IS):**

Within a suspicious set, for each microservice:

- Consider traces containing the suspicious set.
- Count traces with incoming abnormal invocations and traces with outgoing abnormal invocations for that microservice.
- IS is defined as the absolute difference between these counts.

Example (Fig. 2 textual):

- For set `{SA, SB}`, in-set score of B:  
  IS(B) = |3 − 3| = 0  
- In-set score of A:  
  IS(A) = |3 − 0| = 3

Interpretation:

- If a trace contains both incoming and outgoing abnormal invocations on a microservice, the microservice is more likely just affected by others (not causal), and anomaly is just propagated through it.
- If a trace contains only incoming or only outgoing abnormal invocations on a microservice, that microservice is more likely to be the root cause in that trace.
- The difference thus indicates how likely a microservice is a causal anomaly within a suspicious set.

Existing unsupervised trace-based approaches often assume the most upstream abnormal service is the root cause, but anomaly propagation can be:

- Upwards (upstream receives wrong parameters from downstream)
- Downwards (downstream waits too long for upstream)

TraceRCA infers anomaly propagation pattern for each fault rather than assuming a fixed one. Cases where anomaly propagates both upstream and downstream are rare in the studied scenarios.

**Final suspicious score:**

- For every suspicious set containing a microservice:
  - Combine the set’s JI score and the microservice’s in-set score by multiplication (sum is inappropriate due to different scales).
- The final suspicious score of a microservice is the maximum combined score across all suspicious sets containing it.
- Rationale: Although more than one suspicious set can contain a root-cause microservice, a root-cause microservice only affects traces through one main suspicious set.

***

## IV. Experiment

### A. Study Data

Two microservice systems are used as subjects:

1. A widely-used open-source microservice benchmark (Train-Ticket).
2. A large Internet service provider’s production microservice system.

#### 1) Open-Source Microservice System: Train-Ticket

- Train-Ticket contains 41 microservices.
- Deployed with Kubernetes on 7 physical machines (each 12-core 2.4 GHz CPU, 12 GB RAM).
- Each service has multiple instances.
- A workload generator simulates real-world user access patterns.

Faults are constructed via fault injection, following existing work. Three fault types:

- Application bugs
- CPU exhaustion
- Network delay (jam)

Faults are injected at three levels:

- Microservice
- Container
- API

Total 5 injection strategies are summarized in Table I (textual):

- Application Bug (microservice level, 58 cases):  
  Randomly substitute some responses using Istio.
- CPU Exhausted (microservice level, 59 cases):  
  Use `stress-ng` to exhaust CPU.
- Network Delay (microservice, container, API levels, 59, 10, 14 cases respectively):  
  Randomly delay requests using Istio.

To inject a fault of a specific type and level:

- Randomly choose a container/microservice/API.
- Apply corresponding injection.

For multi-root-cause faults:

- Select multiple containers/microservices/APIs and inject simultaneously.

Each fault lasts about 5 minutes.

**Dataset A (Train-Ticket):**

- 200 faults of 5 categories.
- 242,259 traces; 22,675 (9.36%) affected by faults.
- 11 multi-root-cause faults (more than one root-cause microservice).

#### 2) Production Microservice System

- Real-world microservice system with 13 microservices in a large ISP (part of a larger system with more than 50 million users).
- 22 faults of 5 categories:
  - CPU exhaustion
  - Memory exhaustion
  - Host network error
  - Container network error
  - Database failures

**Dataset B:**

- 1,136,825 traces; 17,041 (1.50%) affected by faults.

Overall:

- 222 faults
- 1,379,084 traces
- 39,728 (2.88%) affected by faults

For each fault:

- 20% traces randomly selected as training set for supervised approaches.
- Remaining traces as test set.
- Same fault types and same abnormal trace ratio in training and test.

Unsupervised approaches use only test set.

### B. Overall Performance on Root Cause Localization

Metrics used (following existing work):

- **Top-k accuracy (A@k):** probability that root causes are in top-k results (k = 1, 2, 3).
- **Mean average rank (MAR):** mean of average ranks of root-cause microservices per fault.
- **Mean first rank (MFR):** mean rank of the first root-cause microservice per fault.

Compared approaches:

- Trace-based unsupervised:
  - MicroScope (MS)
  - TraceAnomaly (TA)
- Trace-based supervised:
  - MEPFL with Random Forest (RF)
- Invocation-based unsupervised:
  - RCSF
  - Random Walk (RW) with self and backward edges

MicroScope, TraceAnomaly, and MEPFL localize root causes trace-by-trace; final results are voted by abnormal traces.

- MS is run using TraceRCA’s anomaly detection (the original description is incomplete).
- MEPFL is adapted to collected features; RF chosen for good performance and speed.
- RW uses anomaly severity of microservice pairs as weights.
- TA is extended to all metrics (not just latency) to match settings of TraceRCA.

**Results (Table II textual summary):**

- TraceRCA outperforms all unsupervised approaches on both A and B.
- On A, top-1 accuracy of TraceRCA exceeds unsupervised baselines by 51.02%–81.22%.
- On B, top-1 accuracy improvements are 7.32%–87.23%.
- Across all faults, average top-1 accuracy: 83%; MAR: 1.50.
- TraceRCA outperforms unsupervised approaches by 44.8%–66.1% in top-1 accuracy and 17.2%–78.7% in MAR.

MicroScope and TraceAnomaly assume fixed anomaly propagation patterns. TraceRCA infers the pattern, making it more robust. TraceAnomaly’s anomaly detection is poor when multiple metrics are involved, reducing its localization performance.

**Fault level and multi-root-cause performance (Tables III and IV textual):**

- Across microservice, container, and API-level faults in dataset A:
  - TraceRCA top-1 accuracy: 0.80–0.83.
  - Outperforms unsupervised baselines by 42.86%–300% (top-1).
  - MAR improvements of 12.50%–70.12%.
- For multi-root-cause faults:
  - TraceRCA significantly outperforms all unsupervised approaches on most metrics.
  - Example: top-2 accuracy 0.82, improving by 12.75%–200%; MAR improvement 22.00%–65.79%.

**Conclusion 1:**  
TraceRCA significantly outperforms state-of-the-art unsupervised approaches across all fault levels and for both single-root-cause and multi-root-cause faults.

**Comparison with supervised approach:**  

TraceRCA is slightly inferior to RF (MEPFL) but close:

- On average over A and B:
  - TraceRCA underperforms RF by 10.3% in top-1 accuracy.
  - Underperforms by 9.4% in MAR.

This is expected because supervised approaches have more prior knowledge. However, RF heavily relies on high coverage of fault types and microservices in training data. Modified training sets with missing fault types/microservices show RF’s performance degrades quickly, while unsupervised methods remain more stable and eventually outperform RF.

**Conclusion 2:**  
TraceRCA performs nearly as well as the supervised RF-based method but does not rely on high-quality training data, making it more practical and stable.

### C. Effectiveness of Trace Anomaly Detection

Trace anomaly detection is evaluated using:

- Precision
- Recall
- F1-score

Compared methods:

- TraceRCA’s anomaly detection (TraceRCA-AD)
- Supervised:
  - RF-Trace (MEPFL using RF model)
- Unsupervised:
  - IF (Isolation Forest, invocation-based)
  - TA-AD (TraceAnomaly’s anomaly detection part)

For IF:

- Treat all feature values of an invocation as a multi-dimensional sample.
- Apply IF per microservice pair.
- Detect abnormal traces as in Section III-A.2.

Results:

- Both TraceRCA-AD and RF-Trace achieve F1-score above 0.8.
- TraceRCA-AD is competitive with RF-Trace, despite being unsupervised.
- IF and TA-AD perform poorly due to noisy, multi-feature datasets and lack of feature selection.

RF-Trace’s dependence on high coverage in training data is again confirmed; its F1-score drops quickly when fault types/microservices are missing, while unsupervised methods remain stable and competitive.

Adaptive feature selection’s contribution is examined by comparing TraceRCA-AD with a variant without feature selection (NoSelection). When threshold \(\delta_{ad}\) is high, both show low F1 due to many false negatives. When \(\delta_{ad}\) is low, adaptive feature selection reduces false positives, giving higher F1 for TraceRCA-AD.

**Conclusion 3:**  
The anomaly detection method in TraceRCA performs almost as well as the supervised RF method but is more practical; adaptive feature selection helps maintain good performance.

An additional study injects noise into anomaly detection by randomly flipping detection results with some noise ratio. When noise ratio is under 4%, TraceRCA’s performance does not degrade significantly. When noise ratio exceeds 8%, performance decreases but still stays above other unsupervised approaches. This shows anomaly detection quality impacts all unsupervised methods, but TraceRCA is less sensitive.

Limitations:

- TraceRCA is not able to detect structurally abnormal traces, where unexpected microservice pairs appear but metrics remain normal. Such structural anomalies are rarer but may relate to severe issues like attacks; this is left as future work.

**Conclusion 4:**  
All unsupervised approaches rely on anomaly detection effectiveness, but TraceRCA is less sensitive to detection noise and consistently outperforms other unsupervised approaches.

### D. Impact of Main Parameters

Main parameters:

- \(\delta_{spt}\): support threshold for frequent microservice sets.
- \(k\): number of top suspicious sets for ranking.
- \(\delta_{ad}\): threshold on anomaly severity for abnormal invocations.
- \(\delta_{fs}\): threshold for feature selection.

Findings:

- Top-1 accuracy and MAR remain high across a wide range of \(\delta_{spt}\) and \(k\).
- Even when \(\delta_{ad}\) deviates from its best value, adaptive feature selection keeps F1-score robust.
- F1-score of TraceRCA-AD remains good across varied \(\delta_{fs}\).

**Conclusion 5:**  
TraceRCA is insensitive to each main parameter in a large range, simplifying configuration.

### E. Scalability

Experiments are run on a server with 12 cores and 64 GB RAM. TraceRCA and baselines are implemented in Python.

- Throughput measured as: number of traces handled per second per core.
- TraceRCA is not the fastest, but it is efficient enough for practical use.

Example:

- For a system with 100,000 traces per minute:
  - TraceRCA takes about 60 seconds to localize root cause for a 5-minute fault.

Although feature selection and anomaly detection are done per microservice pair, time complexity is essentially dependent on number of traces.

- Running time is almost linear in number of traces (validated via trace sampling experiments).
- Trace sampling is common in large production systems.

With only 1/16 of all traces, TraceRCA achieves about 80–90% of best performance, indicating good performance even with sampling.

**Conclusion 6:**  
TraceRCA scales well and is practical for large-scale systems.

***

## V. Deployment and Learned Lessons

TraceRCA has been deployed in a production service-oriented system with over 80 services in a large commercial bank. Although the number of services is moderate, it is large-scale in terms of traces (over 100,000 traces per minute). Parameters used match those described in Section III.

Feedback from operators indicates that TraceRCA helps accurately and efficiently localize root-cause microservices and saves significant effort. Several lessons are shared:

1. **Traces are essential for root cause localization.**

   - Invocation-level view only shows relationships between adjacent microservices, whereas traces reveal the relationships among all microservices in a request path.
   - Example (Fig. 15a textual):
     - PLS calls SC or SD directly or via ECT.
     - A fault in ECT affects PLS→ECT invocations and downstream ones (PLS→SC, PLS→SD).
     - Without trace context, relationships among ECT, SC, SD are uncertain, making root cause hard to infer.
     - With traces, all abnormal traces intersect at ECT, enabling straightforward localization.
   - Example (Fig. 15b textual):
     - All microservice pairs are abnormal.
     - Root-cause microservices: SSP and NPS.
     - Without traces, anomaly in NPS might be wrongly attributed to SSP, as NPS depends on SSP and NPS→SSP invocations are abnormal.
     - With traces, it is clear SSP and NPS are independent root causes because most traces containing NPS do not contain SSP.

2. **Abnormal metrics vary across microservices for the same fault.**

   - If a microservice has resource exhaustion, its response rate decreases.
   - Upstream services may experience:
     - Increased response latency (waiting until timeout).
     - Stable or decreased latency but lower success rate (if connections are refused immediately).
   - Therefore, multi-metric anomaly detection is necessary.

3. **Interpretability is important for operator acceptance.**

   - Operators must trust localization results, as wrong results delay mitigation.
   - Different microservices often belong to different teams/departments, so results affect responsibility assignment.
   - In most cases, TraceRCA’s results are interpretable by displaying abnormal traces with invocation normality and highlighting intersections.

***

## VI. Related Work

A large body of work addresses root-cause localization for microservice, service-oriented, component-based, and cloud-native systems. Many approaches can be applied to microservice systems due to similar underlying intuitions.

**Random-walk-based approaches:**

- Idea: perform random walk on a graph of services; microservices that receive more visits are more likely to explain anomalies.
- Improvements include:
  - Second-order random walk
  - Self and backward edges
  - Combination of multiple metrics

**Frequent pattern–based approaches:**

- RCSF mines frequent sequential patterns as root causes directly among call paths from abnormal services to alerting service (not trace-based).

**Supervised trace-based approaches:**

- Use historical or injected faults to train models; idea that similar faults share root causes.
- Limitations:
  - Historical faults are insufficient.
  - Fault injection in production is impractical due to:
    - Cost of maintaining realistic benchmarks.
    - Limited types of injection.

**Unsupervised trace-based approaches:**

- MicroScope, TraceAnomaly:
  - Detect abnormal traces unsupervised.
  - Use causal or dependency graphs to infer root-cause microservices.
  - Often assume fixed propagation patterns or limited metrics.

**Spectrum-based fault localization (SBFL):**

- Widely used for program debugging.
- Uses coverage information (test cases vs program elements) and scoring functions to compute suspiciousness.
- Intuition: program elements executed by many failing tests and few passing tests are more likely to be faulty.
- Similar to TraceRCA’s insight, but:
  - SBFL uses user-defined test cases and does not require anomaly detection.
  - SBFL directly ranks program elements; TraceRCA mines suspicious microservice sets first and then ranks microservices to improve robustness.

***

## VII. Conclusion

TraceRCA is a practical root-cause microservice localization approach via trace analysis, composed of:

- Trace anomaly detection
- Suspicious microservice set mining
- Microservice ranking

Its key insight is that a microservice with more abnormal and fewer normal traces passing through it is more likely to be the root cause. Using a widely-used open-source microservice benchmark and a production system, TraceRCA is shown to localize root causes accurately and efficiently in the largest experimental study in this field so far. Lessons from deployment in a large commercial bank further demonstrate its practicality.

***

## VIII. Acknowledgement

This work was partially supported by:

- National Key R&D Program of China (Grant No. 2019YFE0105500)
- State Key Program of National Natural Science of China (Grant 62072264)
- Beijing National Research Center for Information Science and Technology (BNRist) key projects.
