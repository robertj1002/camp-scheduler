import streamlit as st
import pandas as pd
import random
from typing import List

class Counselor:
    # We add days_off to the setup
    def __init__(self, name: str, is_lifeguard: bool = False, days_off: list = None):
        self.name: str = name
        self.is_lifeguard: bool = is_lifeguard
        self.days_off: list = days_off if days_off else [] # Store the list, or empty list if none
        self.siesta_duties: int = 0
        self.night_duties: int = 0
        self.lifeguard_duties: int = 0
        self.afternoon_offs: int = 0
        
    def __str__(self):
        return self.name

class Cabin:
    def __init__(self, name: str):
        self.name: str = name
        self.counselors: List[Counselor] = []
        
    def add_counselor(self, counselor: Counselor):
        self.counselors.append(counselor)
        
    def get_lifeguards(self) -> List[Counselor]:
        return [c for c in self.counselors if c.is_lifeguard]

def assign_camp_lifeguards(cabins: list, day: str, num_needed: int = 4) -> list:
    """Finds lifeguards, skipping anyone who requested this day off."""
    all_lifeguards = []
    for cabin in cabins:
        # Check if they are a lifeguard AND if today is NOT their day off
        all_lifeguards.extend([c for c in cabin.counselors if c.is_lifeguard and day not in c.days_off])
        
    random.shuffle(all_lifeguards)
    all_lifeguards.sort(key=lambda c: c.lifeguard_duties)
    chosen_lifeguards = all_lifeguards[:num_needed]
    
    for lg in chosen_lifeguards:
        lg.lifeguard_duties += 1
        
    return chosen_lifeguards


def assign_siesta(cabin: Cabin, busy_lifeguards: list, day: str) -> Counselor:
    """Assigns siesta, skipping lifeguards and people taking the day off."""
    # Check if they aren't at the pool AND today is NOT their day off
    available_counselors = [c for c in cabin.counselors if c not in busy_lifeguards and day not in c.days_off]
    
    if not available_counselors:
        return None  
        
    random.shuffle(available_counselors)
    chosen_counselor = min(available_counselors, key=lambda c: c.siesta_duties)
    chosen_counselor.siesta_duties += 1
    
    return chosen_counselor


def assign_night_duty(cabin: Cabin, day: str) -> Counselor:
    """Finds the counselor for night duty, skipping those with the day off."""
    # Filter out anyone who has today off
    available_counselors = [c for c in cabin.counselors if day not in c.days_off]
    
    if not available_counselors:
        return None
        
    random.shuffle(available_counselors)
    chosen_counselor = min(available_counselors, key=lambda c: c.night_duties)
    chosen_counselor.night_duties += 1
    
    return chosen_counselor

# --- STREAMLIT UI ---

st.title("🏕️ Summer Camp Scheduler")

# 1. Sidebar for inputs/settings
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Upload Staff List (CSV or Excel)", type=["csv", "xlsx"])
    
    st.divider() # Adds a clean visual line
    
    # --- NEW RESET BUTTON ---
    if st.button("Reset All Duty Counts"):
        # If cabins exist in memory, delete them
        if 'cabins' in st.session_state:
            del st.session_state['cabins']
        
        # Force the app to immediately reload with a blank slate
        st.rerun()# 2. Process Uploaded File OR Load Dummy Data
        
# 2. Process Uploaded File OR Load Dummy Data
if uploaded_file is not None:
    # Read the file into a pandas DataFrame depending on its type
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    cabins_dict = {}
    
    # Loop through every row in the spreadsheet
    for index, row in df.iterrows():
        cabin_name = str(row['Cabin'])
        counselor_name = str(row['Name'])
        is_lifeguard = bool(row['Is_Lifeguard']) 
        
        # --- DAYS OFF LOGIC ---
        raw_days = str(row.get('Days_Off', ''))
        
        if raw_days.lower() != 'nan' and raw_days.strip() != '':
            # Split "Monday, Tuesday" into a clean list: ["Monday", "Tuesday"]
            days_off_list = [d.strip() for d in raw_days.split(',')]
        else:
            days_off_list = []
        
        if cabin_name not in cabins_dict:
            cabins_dict[cabin_name] = Cabin(cabin_name)
            
        # Pass the new days_off_list into the Counselor setup
        cabins_dict[cabin_name].add_counselor(Counselor(counselor_name, is_lifeguard, days_off_list))
        
    # --- THIS IS THE CRUCIAL LINE THAT PREVENTS THE ERROR ---
    # Save the organized cabins into the app's memory
    st.session_state.cabins = list(cabins_dict.values())
    st.sidebar.success("Staff list loaded successfully!")

elif 'cabins' not in st.session_state:
    # --- FALLBACK DUMMY DATA ---
    cabin_a = Cabin("Cabin A")
    cabin_a.add_counselor(Counselor("Alice", is_lifeguard=True, days_off=["Tuesday"]))
    cabin_a.add_counselor(Counselor("Bob", is_lifeguard=False))
    cabin_a.add_counselor(Counselor("Charlie", is_lifeguard=True)) 
    
    cabin_b = Cabin("Cabin B")
    cabin_b.add_counselor(Counselor("David", is_lifeguard=True, days_off=["Monday", "Wednesday"]))
    cabin_b.add_counselor(Counselor("Eve", is_lifeguard=False))
    cabin_b.add_counselor(Counselor("Frank", is_lifeguard=True)) 

    cabin_c = Cabin("Cabin C")
    cabin_c.add_counselor(Counselor("Grace", is_lifeguard=True))
    cabin_c.add_counselor(Counselor("Hank", is_lifeguard=False))
    cabin_c.add_counselor(Counselor("Ivy", is_lifeguard=True))
    
    st.session_state.cabins = [cabin_a, cabin_b, cabin_c]


# 3. Main Display
st.subheader("Current Cabins & Staff")
for cabin in st.session_state.cabins:
    st.write(f"**{cabin.name}**")
    for c in cabin.counselors:
        role = "Lifeguard" if c.is_lifeguard else "General Staff"
        st.write(f"- {c.name} ({role})")

st.divider()

# 4. Generate Weekly Schedule
if st.button("Generate Weekly Schedule"):
    camp_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
    
    cabin_schedules = {cabin.name: {} for cabin in st.session_state.cabins}
    lifeguard_schedule = {}
    
    for day in camp_days:
        daily_lgs = [] # Keep track of today's lifeguards
        
        # --- 1. Assign Camp-Wide Lifeguards FIRST ---
        if day == "Sunday":
            lifeguard_schedule[day] = ["Not Needed"]
        else:
            daily_lgs = assign_camp_lifeguards(st.session_state.cabins, day, num_needed=4)
            lifeguard_schedule[day] = [lg.name for lg in daily_lgs]
            
        # --- 2. Assign Cabin Duties SECOND ---
        for cabin in st.session_state.cabins:
            if day == "Sunday":
                night_person = assign_night_duty(cabin, day)
                cabin_schedules[cabin.name][day] = {
                    "Siesta": "Not Needed",
                    "Night": night_person.name if night_person else "None"
                }
            else:
                # Pass today's lifeguards into the siesta function so they are skipped
                siesta_person = assign_siesta(cabin, daily_lgs, day)
                night_person = assign_night_duty(cabin, day)
                
                cabin_schedules[cabin.name][day] = {
                    "Siesta": siesta_person.name if siesta_person else "None",
                    "Night": night_person.name if night_person else "None"
                }
                
    st.success("Camp schedule successfully generated!")
    
    # ==============================
    # --- DISPLAY THE RESULTS ---
    # ==============================
    st.header("🌊 Camp-Wide Lifeguard Schedule")
    for day in camp_days:
        if day == "Sunday":
            st.write(f"**{day}:** Not Needed")
        else:
            names_string = ", ".join(lifeguard_schedule[day])
            st.write(f"**{day}:** {names_string}")
            
    st.divider()
    
    st.header("🏕️ Cabin Duties")
    for cabin in st.session_state.cabins:
        st.subheader(f"{cabin.name}")
        for day in camp_days:
            st.write(f"**{day}** | Siesta: {cabin_schedules[cabin.name][day]['Siesta']} | Night: {cabin_schedules[cabin.name][day]['Night']}")
        st.divider()
        

