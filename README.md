# Dynamic Load Balancing in Multiprocessor Systems

## Project Overview
This project is a simulation-based implementation of **dynamic load balancing techniques in multiprocessor systems**, developed as part of the **Operating Systems Theory** course.

In multiprocessor systems, uneven distribution of workload can lead to poor CPU utilization and increased response time. This project focuses on designing and evaluating dynamic load balancing algorithms that continuously monitor system state and redistribute processes to achieve better performance and resource utilization.

The project simulates multiple processors executing tasks with varying workloads and compares different load balancing strategies using performance metrics.

---

## Objectives
- Simulate a multiprocessor system with multiple CPUs.
- Implement dynamic load balancing algorithms.
- Compare different load balancing strategies based on performance metrics.
- Visualize system behavior and performance data.
- Follow proper GitHub workflow with revision tracking and branching.

---

## Features
- Simulation of multiple processors with individual task queues.
- Dynamic task allocation and task migration support.
- Implementation of multiple load balancing strategies:
  - Centralized Least-Loaded Algorithm
  - Distributed Work-Stealing Algorithm
- Runtime monitoring of processor loads and queues.
- Performance metrics calculation:
  - CPU utilization
  - Average waiting time
  - Turnaround time
  - Load imbalance
- Graphical visualization of system performance.
- Modular and extensible code structure.

---

## Project Structure
dynamic-load-balancing-multiprocessor/

|

|── simulation.py # Core simulation and load balancing logic

|── visualization.py # Graph plotting and visualization

|── requirements.txt # Required Python libraries

|── README.md # Project documentation

└── .gitignore # Files ignored by Git

---

## Load Balancing Strategies Implemented

### 1. Centralized Least-Loaded Algorithm
- A central controller assigns tasks to the processor with the smallest queue length.
- Periodic checks are performed to detect load imbalance.
- Tasks are migrated from overloaded processors to underloaded ones.

### 2. Distributed Work-Stealing Algorithm
- Each processor manages its own queue independently.
- When a processor becomes idle, it steals tasks from processors with heavier workloads.
- Reduces central coordination overhead.

---

## Technologies Used
- **Programming Language:** Python
- **Libraries:**
  - `numpy` – numerical computations
  - `matplotlib` – data visualization
  - `pandas` (optional) – data handling and logging
- **Tools:**
  - Git & GitHub for version control
  - VS Code / PyCharm for development

---

## How to Run the Project

### 1. Clone the repository
```bash
git clone <repository-url>
cd dynamic-load-balancing-multiprocessor
```

### 2. Install dependicies
```bash
pip install -r requirements.txt
```

### 3. Run the simulation
```bash
python simulation.py
```

---

## License
- **This project is developed for academic purposes as part of a university course.**



