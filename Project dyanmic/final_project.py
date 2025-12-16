import asyncio
import random
import time
import json
import websockets
import webbrowser
import os
import csv
import logging
from collections import deque
from statistics import mean

# --- CONFIGURATION ---
NODES_COUNT = 4
DEFAULT_POLICY = "work_stealing"

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Sim")

# --- GLOBAL STATE ---
class SimState:
    def __init__(self):
        self.recording = False
        self.csv_file = None
        self.csv_writer = None
        self.scenario_active = False

sim_state = SimState()

# ============================================================================
# PART 1: CORE SIMULATION ENTITIES
# ============================================================================

class Task:
    def __init__(self, tid, work_units):
        self.tid = tid
        self.work_units = work_units
        self.created_at = time.time()
        self.completed_at = None

class Node:
    def __init__(self, nid, scheduler, speed=1.0):
        self.nid = nid
        self.scheduler = scheduler
        self.speed = speed
        self.queue = deque()
        self.busy = False
        self.active = True
        self.completed = 0

    async def run(self):
        while True:
            # Check lifecyle
            if not self.active:
                await asyncio.sleep(0.5)
                continue
            
            # Check for work
            if not self.queue:
                await asyncio.sleep(0.05)
                continue
            
            # Process Task
            task = self.queue.popleft()
            self.busy = True
            
            # Simulate CPU work (Software Delay)
            await asyncio.sleep(task.work_units / self.speed)
            
            # Complete Task
            task.completed_at = time.time()
            self.completed += 1
            self.busy = False
            self.scheduler.report_completion(task)

    def push(self, task):
        if self.active:
            self.queue.append(task)

    def steal_tasks(self, amount=1):
        stolen = []
        if not self.active: return []
        # Steal from the back (tasks not yet started)
        for _ in range(min(amount, max(0, len(self.queue) - 1))):
            stolen.append(self.queue.pop())
        return stolen

    def queue_len(self):
        return len(self.queue)

class Scheduler:
    def __init__(self, num_nodes=4, policy="least_loaded"):
        self.policy = policy
        # Simulate slight hardware variance (Node 0 is 20% faster)
        self.nodes = [Node(i, self, speed=1.0 + (0.2 if i==0 else 0)) for i in range(num_nodes)]
        self.task_queue = asyncio.Queue()
        self.migrations = 0
        self.latencies = []

    async def start(self):
        for n in self.nodes:
            asyncio.create_task(n.run())
        asyncio.create_task(self.assign_loop())
        asyncio.create_task(self.work_stealing_loop())

    async def assign_task(self, task):
        await self.task_queue.put(task)

    async def assign_loop(self):
        rr_index = 0
        while True:
            task = await self.task_queue.get()
            
            active_nodes = [n for n in self.nodes if n.active]
            if not active_nodes:
                await asyncio.sleep(1)
                await self.task_queue.put(task)
                continue

            target = active_nodes[0]
            if self.policy == "round_robin":
                target = active_nodes[rr_index % len(active_nodes)]
                rr_index += 1
            elif self.policy in ("least_loaded", "work_stealing"):
                target = min(active_nodes, key=lambda n: n.queue_len())

            target.push(task)

    async def work_stealing_loop(self):
        while True:
            await asyncio.sleep(0.25)
            if self.policy != "work_stealing": continue

            active_nodes = [n for n in self.nodes if n.active]
            idle_nodes = [n for n in active_nodes if n.queue_len() == 0]
            busiest = max(active_nodes, key=lambda n: n.queue_len()) if active_nodes else None
            
            if idle_nodes and busiest and busiest.queue_len() > 1:
                amount = max(1, busiest.queue_len() // 4)
                stolen = busiest.steal_tasks(amount)
                if stolen:
                    for i, task in enumerate(stolen):
                        idle_nodes[i % len(idle_nodes)].push(task)
                    self.migrations += len(stolen)

    def report_completion(self, task):
        if task.completed_at and task.created_at:
            self.latencies.append(task.completed_at - task.created_at)
            # Keep memory usage low
            if len(self.latencies) > 5000:
                self.latencies = self.latencies[-2000:]

    def kill_node(self, nid):
        if 0 <= nid < len(self.nodes):
            self.nodes[nid].active = False
            dead_tasks = list(self.nodes[nid].queue)
            self.nodes[nid].queue.clear()
            for t in dead_tasks: asyncio.create_task(self.task_queue.put(t))

    def revive_node(self, nid):
        if 0 <= nid < len(self.nodes):
            self.nodes[nid].active = True

    def snapshot(self):
        # Calculate Statistics for the Dashboard
        recent_lats = self.latencies[-50:] if self.latencies else [0]
        avg_lat = mean(recent_lats) if recent_lats else 0
        p95 = sorted(recent_lats)[int(len(recent_lats) * 0.95)] if recent_lats else 0
        
        active_count = sum(1 for n in self.nodes if n.active)
        busy_count = sum(1 for n in self.nodes if n.active and n.busy)
        utilization = (busy_count / active_count * 100) if active_count > 0 else 0

        return {
            "timestamp": time.time(),
            "policy": self.policy,
            "queue_lengths": [n.queue_len() for n in self.nodes],
            "node_status": [n.active for n in self.nodes],
            "completed": [n.completed for n in self.nodes], # Required for new UI
            "migrations": self.migrations,
            "avg_latency": round(avg_lat, 3),
            "p95_latency": round(p95, 3),
            "utilization": round(utilization, 1),
            "recording": sim_state.recording,
            "scenario_active": sim_state.scenario_active
        }

# ============================================================================
# PART 2: WORKLOAD GENERATOR
# ============================================================================

class WorkloadGenerator:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.tid = 0
        self.manual_burst = False
        self.rate_low = 0.3
        self.rate_high = 0.8

    def set_rate(self, low, high):
        self.rate_low = low
        self.rate_high = high
        logger.info(f"Workload Rate Updated: {low}s - {high}s")

    def trigger_burst(self):
        self.manual_burst = True

    async def start(self):
        logger.info("Workload Generator started...")
        while True:
            if self.manual_burst:
                logger.info(">>> BURST TRIGGERED <<<")
                for _ in range(15): await self.create_task()
                self.manual_burst = False
                await asyncio.sleep(1)
                continue

            # Random Traffic
            if random.random() < 0.05:
                for _ in range(5): await self.create_task()
            else:
                await self.create_task()
            
            # Dynamic sleep based on UI settings
            await asyncio.sleep(random.uniform(self.rate_low, self.rate_high))

    async def create_task(self):
        work = random.uniform(0.3, 0.9)
        await self.scheduler.assign_task(Task(self.tid, work))
        self.tid += 1

# ============================================================================
# PART 3: CONTROL LOGIC
# ============================================================================

def toggle_recording():
    if not sim_state.recording:
        os.makedirs("data_logs", exist_ok=True)
        filename = os.path.join("data_logs", f"run_{int(time.time())}.csv")
        sim_state.csv_file = open(filename, "w", newline="")
        sim_state.csv_writer = csv.writer(sim_state.csv_file)
        sim_state.csv_writer.writerow(["timestamp", "policy", "migrations", "utilization", "p95_latency"])
        sim_state.recording = True
        logger.info(f"Recording to: {filename}")
        return True
    else:
        if sim_state.csv_file: sim_state.csv_file.close()
        sim_state.recording = False
        logger.info("Recording stopped.")
        return False

async def run_scenario_logic(scheduler, workload):
    if sim_state.scenario_active: return
    sim_state.scenario_active = True
    logger.info("--- AUTO-SCENARIO STARTED ---")
    
    scheduler.policy = "least_loaded"
    await asyncio.sleep(2)
    
    logger.info("[Scenario] 1. Heavy Burst...")
    workload.trigger_burst()
    await asyncio.sleep(8)
    
    logger.info("[Scenario] 2. Node Failure...")
    scheduler.kill_node(0)
    await asyncio.sleep(6)
    
    logger.info("[Scenario] 3. Recovery...")
    scheduler.revive_node(0)
    await asyncio.sleep(4)
    
    logger.info("[Scenario] 4. Switching to Work Stealing...")
    scheduler.policy = "work_stealing"
    
    logger.info("--- SCENARIO COMPLETE ---")
    sim_state.scenario_active = False

# ============================================================================
# PART 4: WEBSOCKET SERVER
# ============================================================================

clients = set()

async def ws_handler(ws):
    clients.add(ws)
    try:
        async for message in ws:
            data = json.loads(message)
            cmd = data.get("cmd")
            
            if cmd == "burst": global_workload.trigger_burst()
            elif cmd == "policy": global_scheduler.policy = data.get("val")
            elif cmd == "kill": global_scheduler.kill_node(int(data.get("id")))
            elif cmd == "revive": global_scheduler.revive_node(int(data.get("id")))
            elif cmd == "toggle_record": toggle_recording()
            elif cmd == "start_scenario": asyncio.create_task(run_scenario_logic(global_scheduler, global_workload))
            elif cmd == "hello": pass # Handshake
            elif cmd == "download": logger.info("Client requested download (handled client-side).")

            # Handle Rate Change from UI
            elif cmd == "set_rate":
                low = float(data.get("low", 0.3))
                high = float(data.get("high", 0.8))
                global_workload.set_rate(low, high)
            
    except: pass
    finally: clients.remove(ws)

async def broadcaster(scheduler):
    while True:
        snap = scheduler.snapshot()
        msg = json.dumps(snap)
        
        if clients:
            dead = set()
            for c in clients:
                try: await c.send(msg)
                except: dead.add(c)
            for c in dead: clients.remove(c)
        
        if sim_state.recording and sim_state.csv_writer:
            sim_state.csv_writer.writerow([snap["timestamp"], snap["policy"], snap["migrations"], snap["utilization"], snap["p95_latency"]])
            sim_state.csv_file.flush()
            
        await asyncio.sleep(0.15) # 150ms update rate for smooth visuals

# ============================================================================
# MAIN
# ============================================================================

async def main():
    global global_scheduler, global_workload
    logger.info("System Initializing...")
    
    scheduler = Scheduler(num_nodes=NODES_COUNT, policy=DEFAULT_POLICY)
    global_scheduler = scheduler
    workload = WorkloadGenerator(scheduler)
    global_workload = workload

    await scheduler.start()
    asyncio.create_task(workload.start())
    
    # Start WebSocket
    await websockets.serve(ws_handler, "localhost", 8765)
    logger.info("WebSocket running at ws://localhost:8765")
    
    # Auto-open Browser
    try:
        path = os.path.abspath("dashboard.html")
        logger.info(f"Opening Dashboard: {path}")
        webbrowser.open(f"file://{path}")
    except: pass

    await broadcaster(scheduler)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass