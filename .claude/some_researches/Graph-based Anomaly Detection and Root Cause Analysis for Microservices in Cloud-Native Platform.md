# Graph-based Anomaly Detection and Root Cause Analysis for Microservices in Cloud-Native Platform

**Authors**

- 1st Xinwei Wang  
  Beijing University of Posts and Telecommunications  
  State Key Lab of Networking and Switching Technology, Beijing, China  
  buptwxw0316@bupt.edu.cn  

- 2nd Xu Liu\*  
  China Academy of Industrial Internet, Beijing, China  
  liuxu@china-aii.com  

- 3rd Peng Xu  
  Beijing University of Posts and Telecommunications  
  State Key Lab of Networking and Switching Technology, Beijing, China  
  xupeng@bupt.edu.cn  

- 4th Haoran Du  
  Beijing University of Posts and Telecommunications  
  State Key Lab of Networking and Switching Technology, Beijing, China  
  duhaoran@bupt.edu.cn  

\*Corresponding author  

***

## Abstract

Due to the excellent characteristics of microservices architecture, such as high scalability, high fault tolerance, and ease of maintenance, and the flexible, efficient, and scalable deployment environment provided by cloud-native platforms, an increasing number of applications are being constructed based on microservices architecture. In such scenarios, the complexity of anomaly detection rises sharply due to the involvement of numerous interrelated microservices components and the complex invocation relationships among these components in each microservices application. Existing anomaly detection methods struggle to maintain sufficient accuracy in such complex environments.

To address this challenge, this paper proposes the **Graph-based Anomaly Detection and Root Cause Analysis (GADRCA)** method for Microservices in Cloud-Native Platform. This method leverages graph structures to comprehensively consider the fundamental distribution characteristics of multiple resource consumption metrics involved in the runtime of microservices applications, such as response time, CPU usage, and memory usage. It also preserves the structural information of trace data within microservices to achieve more comprehensive anomaly detection. Upon identifying anomalous traces, the method determines the direction of anomaly propagation using a trace root cause analysis approach based on multiple metric anomaly types. Finally, a topological graph approach is employed to accurately pinpoint the root cause service. The method’s effectiveness in enhancing anomaly detection and root cause analysis is demonstrated through a series of experiments.

**Index Terms** — Anomaly Detection, Root Cause Analysis, Microservices, Cloud-Native

***

## I. Introduction

Due to the excellent characteristics of microservices architecture, such as high scalability and high fault tolerance, an increasing number of applications are being constructed based on microservices architecture. Simultaneously, cloud-native platforms not only provide a convenient operating environment for microservices but also facilitate easy access to resource consumption metrics for each microservice based on its observability.

Microservices applications require extensive collaboration among components during runtime, posing challenges for their operational maintenance. To achieve precise anomaly detection, thorough analysis of the dependencies among these components and their resource utilization during operation is essential. Researchers have embraced trace techniques to enhance the efficacy of anomaly detection in microservices applications. This technique constructs a comprehensive service request flowchart, accurately documenting the invocation information and execution status between services, thereby providing crucial support for anomaly detection.

However, there remain two primary challenges in trace anomaly detection and root cause analysis:

- **Integration of traces and metrics with structure preserved.**  
  How to effectively integrate trace data with multiple resource usage metrics while still comprehensively considering the structural information of the traces. Current methods often vectorize trace data to incorporate resource usage metrics, but this vectorization can lead to the loss of structural information, thereby reducing anomaly detection performance.

- **Propagation direction and anomaly-type-aware RCA.**  
  How to accurately determine the propagation direction based on the anomaly types corresponding to different metrics to locate the root cause services. Traditional root cause analysis methods suffer from simplified processing, low traversal efficiency, and neglecting the impact of multiple anomaly types on the propagation direction.

To address these challenges, this paper proposes the **Graph-based Anomaly Detection and Root Cause Analysis (GADRCA)** method for Microservices in Cloud-Native Platform. This method considers the fundamental distribution characteristics of multiple resource consumption metrics involved in the runtime of microservices applications, while preserving the structural information of trace data within microservices based on graph structures to achieve more comprehensive anomaly detection. Additionally, this study incorporates the identified anomaly types after detection to determine the propagation direction of anomalies and ultimately uses a topological graph method to pinpoint the root cause services.

***

## II. Related Work

This section introduces related work on trace-based anomaly detection and root cause analysis methods.

### A. Trace-based Anomaly Detection

Regarding trace-based anomaly detection, based on the source of trace data, methods are mainly categorized into:

- **Log-based trace construction**
- **Monitoring tool–based trace collection**

This paper focuses on trace collection based on monitoring tools for trace-based anomaly detection.

Representative methods include:

- **AEVB:**  
  An unsupervised deep Bayesian network model for detecting anomalies in trace response times.

- **Seer:**  
  Uses CNN for dimensionality reduction and LSTM to learn temporal and spatial patterns in trace data, effectively analyzing and predicting QoS.

- **Multimodal LSTM:**  
  Learns and detects anomalies in both trace call paths and response times.

- **TraceAnomaly and CRISP:**  
  Represent traces as service trace vectors (STVs) and use VAE to detect anomalies in call paths and response times.

These methods typically vectorize trace data to facilitate the use of resource consumption metrics, but vectorization may cause partial loss of structural information in trace data and thus reduce anomaly detection performance.

### B. Trace-based Root Cause Analysis

After detecting anomalous traces, root cause analysis is required to pinpoint the specific service responsible for the anomaly. Trace-based root cause analysis methods primarily use:

- Visualization techniques
- Direct analysis
- Topology-based approaches

This paper focuses on topology-based approaches.

Topology-based methods visualize relationships and dependencies among services by plotting the topology of traces, reflecting anomaly propagation paths. For example, MonitorRank and MicroHECL utilize topology graphs to identify potential root causes. They rely on trace data including timestamps, source and destination services, metrics, and request IDs, reconstruct service traces for the same user request, and build the application topology.

In cloud-native platforms with complex invocation relationships and various anomaly types, these methods often:

- Simplify processing,
- Exhibit low traversal efficiency,
- Neglect certain anomaly types,

which can lead to inaccurate root cause analysis.

***

## III. Methodology

Based on the above survey, this paper proposes the **Graph-based Anomaly Detection and Root Cause Analysis (GADRCA)** for Microservices in Cloud-Native Platform.

### A. Methodology Overview

In microservices, a trace constructs a comprehensive service request flowchart, capturing the entire process from the initiation of service requests through interactions among various services, accurately documenting internal service invocation details and execution status.

Resource consumption metrics typically include:

- CPU utilization
- Memory usage
- Disk throughput
- Network throughput
- Response time of calls

These metrics, along with trace data, collectively form the characteristics of a trace used for anomaly detection and root cause analysis.

In GADRCA:

1. A **graph-based trace anomaly detection method** is used.  
   Structural anomaly detection of traces and anomaly detection of trace metrics are integrated to obtain the negative log-likelihood (NLL) and identify anomalous traces.

2. A collection of **potential anomalous services** is constructed from all services involved in anomalous traces.

3. Combining this set of anomalous services with anomaly types corresponding to resource metrics, an **anomaly type–based trace root cause analysis** method is applied to pinpoint root cause services.

Fig. 1 (textual): Overall architecture of GADRCA:

- Input: trace graphs plus metrics.
- Two VAEs:
  - Trace structure VAE.
  - Trace metrics VAE.
- NLL as anomaly score.
- Anomaly types determine propagation direction.
- Topological graph plus DFS used for RCA.

### B. Graph-based Trace Anomaly Detection

To address potential loss of structural information in trace vectorization, this paper proposes a **Graph-based Trace Anomaly Detection** method.

Key ideas:

- Represent each trace as a graph:
  - Nodes: services
  - Edges: invocation relationships
  - Node attributes: resource consumption metrics

This representation preserves structural information of the trace while considering resource metrics, thereby improving accuracy and comprehensiveness of anomaly detection.

A trace is represented as a graph:

\[
G = (A, X, Y)
\]

- \(A\): \(N \times N\) adjacency matrix, representing invocation relationships (if node \(a\) is parent of node \(b\), \(A_{a,b} = 1\)).
- \(X\): metric matrices, each \(N \times 1\), specifically:
  - \(X_1\): response time
  - \(X_2\): CPU usage
  - \(X_3\): memory usage
  - \(X_4\): disk throughput
  - \(X_5\): network throughput
- \(Y\): \(N \times 1\) matrix, each row containing a service ID.

**Types of trace anomalies:**

- **Structural anomalies:**  
  A node is expected to call another node but fails to do so; missing nodes/edges in the graph.

- **Resource metric anomalies:**  
  Significant changes in resource metrics of some nodes. Detection requires neighborhood evaluation, as metrics of a node are mainly influenced by neighbors.

These two anomaly types require encoding both structure and metrics via two separate networks.

**Use of Variational Autoencoders (VAE):**

Trace data includes multi-dimensional information (structure, metrics). VAE can:

- Map multi-dimensional data into a latent space.
- Detect anomalies via reconstruction error.

Let trace data be represented as \(x\). The VAE models:

\[
p_\theta(x) = \mathbb{E}_{p_\lambda(z)}[p_\theta(x | z)]
\]

with latent variable \(z\) and prior \(p_\lambda(z)\). Training maximizes ELBO:

\[
\log p_\theta(x) \ge \mathbb{E}_{q_\phi(z|x)} [\log p_\theta(x | z) + \log p_\lambda(z) - \log q_\phi(z | x)]
\]

In GADRCA, the graph-based trace VAE has two components:

- **Trace Structure VAE** (captures structural features ⇒ latent \(z_1\)).
- **Trace Metrics VAE** (captures metric features ⇒ latent \(z_2\)).

#### 1) Trace Structure VAE

Fig. 2 (textual): Network structure:

- Input: adjacency matrix \(A\) and service ID matrix \(Y\).
- Encoder:
  - Graph Neural Network (GNN) to extract node-level features.
  - Pooling layer to aggregate node features into a graph-level representation.
  - Outputs latent structural vector \(z_1\).
- Decoder:
  - MLP to reconstruct graph data from \(z_1\).
  - Inner-product decoder to reconstruct symmetric adjacency matrix \(\hat{A}\).
  - GNN to reconstruct \(Y\) to preserve service information.

#### 2) Trace Metrics VAE

Fig. 3 (textual): Network structure:

- Inputs: \(A\), metrics \(X_1\)–\(X_5\), and \(Y\).
- Encoder:
  - Similar GNN + Pooling to process structure and metrics jointly, outputting \(z_2\).

- Decoder:
  - **Dispatching layer** bridges metric matrices \(X_1\)–\(X_5\) and \(Y\), integrating node-level metrics with service IDs.
  - Multiple GNNs, one per metric, reconstruct metric data separately to capture different distributions and relationships.
  - This preserves metric information for each node and integrates service IDs.

#### 3) Joint Model and NLL

The final Graph-based Trace Anomaly Detection model:

\[
p_{\theta,\lambda}(G, z_1, z_2) = p_\theta(A, Y | z_1) p_\lambda(z_1) \cdot p_\theta(X_1,\dots,X_5 | A, Y, z_2) p_\lambda(z_2 | z_1)
\]

- \(p_\theta(A, Y | z_1)p_\lambda(z_1)\): structure VAE with encoder \(q_\phi(z_1 | A, Y)\) and decoder \(p_\theta(A, Y | z_1)\).
- \(p_\theta(X_1,\dots,X_5 | A, Y, z_2)p_\lambda(z_2 | z_1)\): metrics VAE with encoder \(q_\phi(z_2 | A, X, Y)\) and decoder \(p_\theta(X | A, Y, z_2)\).

**Algorithm 1 (textual): Graph-based Trace Anomaly Detection**

Inputs:

- Graph \(G = (A, X, Y)\)
- Training data for \(A\), \(X\), service IDs \(Y\)

Steps:

1. Encode structure: \(q_\phi(z_1 | A, Y)\).
2. Sample/compute \(p_\lambda(z_1)\).
3. Decode structure: \(p_\theta(A, Y | z_1)\).
4. Encode metrics: \(q_\phi(z_2 | A, X, Y)\).
5. Model \(p_\lambda(z_2 | z_1)\).
6. Decode metrics: \(p_\theta(X | A, Y, z_2)\).
7. Maximize ELBO (equivalently minimize negative ELBO as loss \(L\)).
8. Iterate over training data, minimizing \(L\).

**Anomaly score: Negative Log-Likelihood (NLL)**

\[
\text{NLL}(G) = -\log p_m(G) = -\log \mathbb{E}_{q_\phi(z_1,z_2|G)} \left[\frac{p_{\theta,\lambda}(G, z_1, z_2)}{q_\phi(z_1, z_2 | G)}\right]
\]

- Higher NLL ⇒ lower fit ⇒ more likely anomalous trace.

Summary:

- Trace Structure VAE detects structural anomalies.
- Trace Metrics VAE detects resource-metric anomalies.
- NLL is the final anomaly score.

### C. Anomaly Type–based Trace Root Cause Analysis

After identifying anomalous traces, specific anomalous services must be located. Many existing methods oversimplify processes, have inefficient traversal, and overlook anomaly types. This paper proposes **Anomaly Type–based Trace Root Cause Analysis**:

- Determines propagation direction according to anomaly types corresponding to different metrics.
- Uses a topological graph approach to locate root cause services.

From Graph-based Trace Anomaly Detection:

- Anomalous traces are identified by NLL.
- Trace Structure VAE and Trace Metrics VAE provide details:
  - Structural anomalies.
  - Anomalies in response time, CPU, memory, disk throughput, network throughput.

By analyzing structural and metric anomalies, **application-level anomaly types** are determined:

1. **Invocation Anomaly**
   - Characterized by service invocation failures.
   - Identified from structural anomalies in traces.
   - A structural anomaly indicates a service fails to invoke its subsequent service, interrupting the trace.
   - The downstream service where invocation fails is the root cause.
   - Propagation direction: **downstream → upstream** (upstream callers are affected).

2. **Performance Anomaly**
   - Characterized by abnormal resource usage metrics.
   - Caused by internal resource issues within a service.
   - Propagation direction: **downstream → upstream**, gradually impacting upstream services and overall trace performance.

3. **Traffic Anomaly**
   - Characterized by abnormal network throughput.
   - May result from network congestion, attacks, or other network issues.
   - Propagation direction: **upstream → downstream**, as external factors often affect upstream entry services first and then downstream services.
   - The upstream service where traffic anomaly originates is the root cause.

**Propagation chain analysis:**

- When an anomalous trace is identified:
  - All services in the trace form a **potential anomalous service set**.
  - Application-level anomaly types are determined for each anomaly.
  - Propagation chain analysis determines the root cause.

Process:

- Select a potential anomalous service as an entry point.
- Determine its anomalous neighbors (upstream/downstream).
- According to anomaly type, compare theoretical propagation direction with actual distribution of metric anomalies.
- If aligned, follow propagation iteratively until reaching a service where resource metrics are no longer anomalous; this is identified as the root cause.

Fig. 4 (textual): Example of anomaly propagation analysis:

- Two anomalous traces:
  - A–B–D–G–J
  - A–B–E
- Potential anomalous service set: A, B, D, E, G, J plus their anomalous calls.

Example steps:

- Choose service D as entry.
- Neighboring anomalous services: B and G.
- If call B–D shows network throughput anomaly, anomaly type is traffic anomaly (upstream → downstream). Root cause is upstream.
- D is downstream of B ⇒ direction matches.
- Then analyze B:
  - If call A–B also has network throughput anomaly, A is the most upstream service with anomaly ⇒ A is root cause.

**Implementation:**

- Use **topological sorting** to determine order of services, identifying propagation path.
- Use **Depth-First Search (DFS)**:
  - Start from anomalous service.
  - Recursively explore neighbors to find all affected services.
  - This captures full propagation path and identifies root cause.

***

## IV. Evaluation

This section validates GADRCA via experiments, describing datasets, metrics, and baselines, followed by results.

### A. Datasets

Two widely used open-source microservices benchmark datasets:

- **Train-Ticket dataset**
- **AIOps Challenge dataset**

These datasets are typically used to evaluate performance and reliability of microservices architectures.

**Table I: Overview of datasets**

| Name        | Microservices | Physical Machines | Total Data |
|------------|---------------|-------------------|------------|
| Train-Ticket | 41          | 7                 | 242,259    |
| AIOps        | 40          | 6                 | 421,984    |

### B. Evaluation Metrics and Baseline Methods

Evaluation metrics:

- Precision \(P\)
- Recall \(R\)
- F1-score \(F_1\)

\[
P = \frac{TP}{TP + FP},\quad
R = \frac{TP}{TP + FN},\quad
F_1 = 2 \cdot \frac{P \cdot R}{P + R}
\]

Baseline methods:

- Multimodal LSTM
- TraceAnomaly
- CRISP

These are compared with GADRCA.

### C. Experimental Results

The experiments include comparative and ablation studies. Some baseline results are taken from prior work.

**Comparative experiments:**

- GADRCA achieves higher accuracy than existing methods.
- **Multimodal LSTM:**
  - Considers trace structure and response time.
  - Model complexity may reduce sensitivity to anomalies.
- **TraceAnomaly:**
  - Captures structure and response time anomalies.
  - Ignores other key metrics, making detection less comprehensive.
- **CRISP:**
  - Focuses on anomaly detection in critical paths.
  - Ignores anomalies in non-critical paths, reducing overall accuracy.

**Table II: Comparison of experimental results**

| Datasets    | Methods           | Precision | Recall | F1-Score |
|------------|-------------------|-----------|--------|----------|
| Train-Ticket | Multimodal LSTM | 0.602     | 0.747  | 0.666    |
|            | TraceAnomaly      | 0.834     | 0.882  | 0.857    |
|            | CRISP             | 0.893     | 0.915  | 0.904    |
|            | **GADRCA**        | **0.926** | **0.938** | **0.932** |
| AIOps      | Multimodal LSTM  | 0.633     | 0.716  | 0.672    |
|            | TraceAnomaly      | 0.811     | 0.853  | 0.831    |
|            | CRISP             | 0.891     | 0.902  | 0.896    |
|            | **GADRCA**        | **0.915** | **0.923** | **0.919** |

GADRCA outperforms baselines on all metrics, especially F1-score. Its advantages come from:

- Graph-based representation preserving trace structure.
- Use of a wider range of resource metrics.

**Ablation experiments:**

Components systematically removed:

1. **Graph structure**  
   - Replace graph-based trace construction with Multimodal LSTM-style trace construction (no graph).
2. **Multi-metric VAE**  
   - Replace multi-metric VAE with VAE from TraceAnomaly.

**Table III: Ablation results on Train-Ticket**

| Methods          | Precision | Recall | F1-Score |
|------------------|-----------|--------|----------|
| GADRCA           | 0.926     | 0.938  | 0.932    |
| w/o Graph structure | 0.638  | 0.796  | 0.708    |
| w/o Multi-Metric | 0.872     | 0.896  | 0.884    |

Conclusions:

- **Graph structures are crucial** for structure anomaly detection:
  - Removing graph structure causes significant performance drop.
  - F1-score decreases by about 24%.
- **Multiple metrics play a key role**:
  - Removing multi-metric VAE leads to noticeable decline in Precision, Recall, and F1-score.
  - F1-score drops by about 5%.
  - Considering multiple metrics improves anomaly detection accuracy.

These results demonstrate that graph structures and multiple metrics in GADRCA significantly improve anomaly detection and root cause analysis.

***

## V. Conclusion

This paper introduces **Graph-based Anomaly Detection and Root Cause Analysis (GADRCA)** for Microservices in Cloud-Native Platform. The methodology:

- Harnesses graph structures.
- Incorporates multiple metrics related to anomaly types.
- Implements a full-chain algorithm from anomaly detection to root cause analysis.

A series of experiments show that GADRCA surpasses baseline approaches such as Multimodal LSTM, TraceAnomaly, and CRISP in anomaly detection accuracy. It provides strong support for comprehensive anomaly detection and root cause analysis for microservices in cloud-native platforms.
