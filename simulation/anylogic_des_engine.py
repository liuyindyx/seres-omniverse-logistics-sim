"""
AnyLogic-Style Discrete-Event Simulation (DES) Engine
======================================================
Simulates automotive production line mechanics:
- 60 JPH takt time vehicle progression (60 seconds per car)
- 40-station bill of materials (BOM) consumption
- Dynamic Kanban replenishment requests
- AGV fleet dispatching (Single-carrier vs. 1-to-4 Tugger Train Milk Run)
- Starvation event detection and bottleneck analysis
"""

import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from simulation.workshop_specs import get_seres_40_stations, StationSpecification, PartSpecification

@dataclass(order=True)
class KanbanTask:
    priority: float
    created_time: float = field(compare=False)
    station_id: int = field(compare=False)
    side: str = field(compare=False)
    part_id: str = field(compare=False)
    part_name: str = field(compare=False)
    target_pos: tuple = field(compare=False)
    handling_time: float = field(compare=False)
    delivery_sets: int = field(compare=False)

@dataclass
class AGVState:
    agv_id: int
    is_busy: bool = False
    current_pos: tuple = (140.0, -32.0)
    available_at_time: float = 0.0
    total_trips: int = 0
    total_distance_traveled: float = 0.0
    total_busy_time: float = 0.0

class DiscreteLogisticsSimulator:
    """Discrete-event engine evaluating production shift logistics feasibility."""

    def __init__(self, takt_time_sec: float = 60.0, agv_count: int = 6, shift_hours: float = 2.0):
        self.takt_time_sec = takt_time_sec
        self.agv_count = agv_count
        self.shift_seconds = shift_hours * 3600.0
        self.stations = get_seres_40_stations()
        self.supermarket_pos = (140.0, -32.0)
        self.agv_speed_loaded = 1.2 # m/s
        self.agv_speed_empty = 1.5  # m/s
        self.warehouse_pickup_sec = 25.0

    def run_simulation(self, 
                       mode: str = "baseline", 
                       agv_count_override: Optional[int] = None) -> Dict[str, Any]:
        """Runs the simulation under either baseline or agent-optimized logistics policy.
        
        Args:
            mode: 'baseline' (single carrier AGV, central warehouse)
                  'optimized' (1-to-4 tugger train, 3-zone SPS supermarkets, fast docking)
            agv_count_override: custom AGV fleet size
        """
        fleet_size = agv_count_override if agv_count_override is not None else (36 if mode == "optimized" else self.agv_count)
        
        inventories = {}
        max_capacities = {}
        trigger_levels = {}
        
        for st in self.stations:
            if mode == "optimized":
                # High-density modular flow racks (capacity expanded to 6-12 sets)
                l_cap = max(6, int(st.left_part.rack_capacity_sets * 1.8))
                r_cap = max(6, int(st.right_part.rack_capacity_sets * 1.8))
                l_trigger = max(3, l_cap - 2)
                r_trigger = max(3, r_cap - 2)
            else:
                l_cap = st.left_part.rack_capacity_sets
                r_cap = st.right_part.rack_capacity_sets
                l_trigger = st.left_part.kanban_min_trigger
                r_trigger = st.right_part.kanban_min_trigger

            inventories[st.station_id] = {"Left": l_cap, "Right": r_cap}
            max_capacities[st.station_id] = {"Left": l_cap, "Right": r_cap}
            trigger_levels[st.station_id] = {"Left": l_trigger, "Right": r_trigger}

        agvs = [AGVState(agv_id=i+1) for i in range(fleet_size)]
        
        task_queue: List[KanbanTask] = []
        pending_deliveries = [] # (arrival_time, station_id, side, delivery_sets)
        pending_requests = set() # (st_id, side)
        
        starvation_events = []
        total_parts_consumed = 0
        total_parts_delivered = 0
        stockout_occurrences = {st.station_id: 0 for st in self.stations}
        
        cycle_count = int(self.shift_seconds // self.takt_time_sec)

        # Main timeline simulation loop
        for cycle in range(cycle_count):
            current_time = cycle * self.takt_time_sec

            # Step 1: Process arriving deliveries at or before current_time
            remaining_deliveries = []
            for item in pending_deliveries:
                arr_time, st_id, side, sets = item
                if arr_time <= current_time:
                    inventories[st_id][side] = min(max_capacities[st_id][side], inventories[st_id][side] + sets)
                    total_parts_delivered += sets
                    pending_requests.discard((st_id, side))
                else:
                    remaining_deliveries.append(item)
            pending_deliveries = remaining_deliveries

            # Step 2: Update AGV availability
            for agv in agvs:
                if agv.is_busy and agv.available_at_time <= current_time:
                    agv.is_busy = False

            # Step 3: Production line advances - consume parts at all 40 stations
            for st in self.stations:
                st_id = st.station_id
                
                # Consume Left
                if inventories[st_id]["Left"] > 0:
                    inventories[st_id]["Left"] -= 1
                    total_parts_consumed += 1
                else:
                    stockout_occurrences[st_id] += 1
                    starvation_events.append({
                        "time_sec": current_time,
                        "time_min": round(current_time / 60.0, 1),
                        "cycle": cycle,
                        "station_id": st_id,
                        "station_name": st.station_name,
                        "side": "Left",
                        "part_name": st.left_part.part_name,
                        "reason": "缺料停线 (Stockout) - AGV未能及时送达"
                    })

                # Consume Right
                if inventories[st_id]["Right"] > 0:
                    inventories[st_id]["Right"] -= 1
                    total_parts_consumed += 1
                else:
                    stockout_occurrences[st_id] += 1
                    starvation_events.append({
                        "time_sec": current_time,
                        "time_min": round(current_time / 60.0, 1),
                        "cycle": cycle,
                        "station_id": st_id,
                        "station_name": st.station_name,
                        "side": "Right",
                        "part_name": st.right_part.part_name,
                        "reason": "缺料停线 (Stockout) - AGV未能及时送达"
                    })

                # Step 4: Kanban triggers
                if inventories[st_id]["Left"] <= trigger_levels[st_id]["Left"]:
                    req_key = (st_id, "Left")
                    if req_key not in pending_requests:
                        pending_requests.add(req_key)
                        target_x = st.pos_x + st.length / 2.0
                        target_y = 5.0
                        prio = float(inventories[st_id]["Left"]) if mode == "optimized" else current_time
                        delivery_batch = max_capacities[st_id]["Left"]
                        task = KanbanTask(
                            priority=prio,
                            created_time=current_time,
                            station_id=st_id,
                            side="Left",
                            part_id=st.left_part.part_id,
                            part_name=st.left_part.part_name,
                            target_pos=(target_x, target_y),
                            handling_time=st.left_part.handling_time_sec,
                            delivery_sets=delivery_batch
                        )
                        heapq.heappush(task_queue, task)

                if inventories[st_id]["Right"] <= trigger_levels[st_id]["Right"]:
                    req_key = (st_id, "Right")
                    if req_key not in pending_requests:
                        pending_requests.add(req_key)
                        target_x = st.pos_x + st.length / 2.0
                        target_y = -5.0
                        prio = float(inventories[st_id]["Right"]) if mode == "optimized" else current_time
                        delivery_batch = max_capacities[st_id]["Right"]
                        task = KanbanTask(
                            priority=prio,
                            created_time=current_time,
                            station_id=st_id,
                            side="Right",
                            part_id=st.right_part.part_id,
                            part_name=st.right_part.part_name,
                            target_pos=(target_x, target_y),
                            handling_time=st.right_part.handling_time_sec,
                            delivery_sets=delivery_batch
                        )
                        heapq.heappush(task_queue, task)

            # Step 5: Dispatch AGVs
            batch_capacity = 4 if mode == "optimized" else 1

            while task_queue:
                idle_agv = next((a for a in agvs if not a.is_busy), None)
                if not idle_agv:
                    break

                dispatched_tasks = []
                for _ in range(batch_capacity):
                    if task_queue:
                        dispatched_tasks.append(heapq.heappop(task_queue))

                if mode == "optimized":
                    # Decentralized Zoned Supermarkets (Trim at 70m, Chassis at 175m, Final at 245m)
                    lead_task = dispatched_tasks[0]
                    wh_x = 70.0 if lead_task.station_id <= 20 else (175.0 if lead_task.station_id <= 30 else 245.0)
                    wh_y = -20.0
                    
                    max_st_x = max(t.target_pos[0] for t in dispatched_tasks)
                    min_st_x = min(t.target_pos[0] for t in dispatched_tasks)
                    transit_dist = abs(wh_x - min_st_x) + (max_st_x - min_st_x) + abs(wh_y) + 8.0
                    
                    t_pickup = 25.0
                    t_travel = transit_dist / self.agv_speed_loaded
                    t_dropoffs = sum(12.0 for _ in dispatched_tasks) # Automatic roller transfer: 12s
                    t_return = transit_dist / self.agv_speed_empty
                    
                    total_trip = t_pickup + t_travel + t_dropoffs + t_return
                    
                    running_time = current_time + t_pickup + (t_travel * 0.5)
                    for t in dispatched_tasks:
                        running_time += 12.0
                        pending_deliveries.append((running_time, t.station_id, t.side, t.delivery_sets))
                        
                    idle_agv.is_busy = True
                    idle_agv.available_at_time = current_time + total_trip
                    idle_agv.total_trips += 1
                    idle_agv.total_distance_traveled += (transit_dist * 2.0)
                    idle_agv.total_busy_time += total_trip
                else:
                    # Centralized single-carrier
                    t = dispatched_tasks[0]
                    dist_x = abs(t.target_pos[0] - self.supermarket_pos[0])
                    dist_y = abs(t.target_pos[1] - self.supermarket_pos[1])
                    eff_dist = dist_x + dist_y
                    
                    t_pickup = self.warehouse_pickup_sec
                    t_to_st = eff_dist / self.agv_speed_loaded
                    t_unload = t.handling_time
                    t_return = eff_dist / self.agv_speed_empty
                    
                    total_trip = t_pickup + t_to_st + t_unload + t_return
                    arrival_time = current_time + t_pickup + t_to_st + t_unload
                    
                    idle_agv.is_busy = True
                    idle_agv.available_at_time = current_time + total_trip
                    idle_agv.total_trips += 1
                    idle_agv.total_distance_traveled += (eff_dist * 2.0)
                    idle_agv.total_busy_time += total_trip
                    pending_deliveries.append((arrival_time, t.station_id, t.side, t.delivery_sets))

        avg_utilization = sum(min(1.0, a.total_busy_time / self.shift_seconds) for a in agvs) / len(agvs) * 100.0
        
        top_starved = sorted(
            [{"station_id": sid, "starvation_count": cnt, "name": next(s.station_name for s in self.stations if s.station_id == sid)} 
             for sid, cnt in stockout_occurrences.items() if cnt > 0],
            key=lambda x: x["starvation_count"],
            reverse=True
        )

        can_arrive_on_time = (len(starvation_events) == 0)

        return {
            "mode": mode,
            "shift_hours": self.shift_seconds / 3600.0,
            "takt_time_sec": self.takt_time_sec,
            "agv_fleet_size": fleet_size,
            "cars_produced": cycle_count,
            "total_parts_delivered": total_parts_delivered,
            "starvation_events_count": len(starvation_events),
            "can_arrive_on_time": can_arrive_on_time,
            "agv_fleet_utilization_pct": round(avg_utilization, 2),
            "starved_stations_count": len(top_starved),
            "top_starved_stations": top_starved[:5],
            "summary": (
                f"【来得及检验 ({mode.upper()})】: 节拍 {self.takt_time_sec}s/车，AGV车队: {fleet_size}台。"
                f"缺料停线: {len(starvation_events)}次 (准时闭环: {can_arrive_on_time})。"
                f"车队负荷利用率: {round(avg_utilization, 1)}%。"
            )
        }

if __name__ == "__main__":
    sim = DiscreteLogisticsSimulator()
    print(sim.run_simulation(mode="baseline")["summary"])
    print(sim.run_simulation(mode="optimized", agv_count_override=36)["summary"])
