import streamlit as st
import sqlite3
import hashlib
from web3 import Web3
import json

# --- BLOCKCHAIN CONFIGURATION ---
RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/CFxXzoYXrLaFvVyBtt36G" 
CONTRACT_ADDRESS = "0xd17631ccC02a2e7e962B9Da98bEf8cd815BD9328"
# This is the NEW ABI for the multi-election contract
CONTRACT_ABI = json.loads('[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"string","name":"_name","type":"string"}],"name":"addCandidate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"admin","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"_name","type":"string"}],"name":"createElection","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"uint256","name":"_candidateId","type":"uint256"}],"name":"deleteCandidate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"uint256","name":"_candidateId","type":"uint256"},{"internalType":"string","name":"_newName","type":"string"}],"name":"editCandidate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"electionCandidates","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"name","type":"string"},{"internalType":"uint256","name":"voteCount","type":"uint256"},{"internalType":"bool","name":"isActive","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"elections","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"name","type":"string"},{"internalType":"uint256","name":"candidatesCount","type":"uint256"},{"internalType":"bool","name":"exists","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"electionsCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"uint256","name":"_candidateId","type":"uint256"}],"name":"getCandidate","outputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"string","name":"","type":"string"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"string","name":"","type":"string"}],"name":"hasVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"uint256","name":"_candidateId","type":"uint256"},{"internalType":"string","name":"_voterId","type":"string"}],"name":"vote","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

w3 = Web3(Web3.HTTPProvider(RPC_URL))
ADMIN_PRIVATE_KEY = "12d33d0196a3798ca180724f868fda729b8bf6d0c2b96cccd0a2f1e3e77ddead" 
ADMIN_ADDRESS = "0xfdF82A668AC38D04bE797852A47928e4eDbd4b14"

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('voters.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (reg_no TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT, password TEXT)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- HELPER FUNCTIONS ---
def send_transaction(func):
    nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)
    tx = func.build_transaction({
        'chainId': w3.eth.chain_id,
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=ADMIN_PRIVATE_KEY)
    # Using raw_transaction for web3.py v6+ compatibility
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction) 
    return w3.eth.wait_for_transaction_receipt(tx_hash)

def fetch_all_elections():
    try:
        count = contract.functions.electionsCount().call()
        elections = []
        for i in range(1, count + 1):
            elec = contract.functions.elections(i).call()
            if elec[3]: # If exists
                elections.append({"id": elec[0], "name": elec[1], "cand_count": elec[2]})
        return elections
    except Exception as e:
        return []

def fetch_active_candidates(election_id, cand_count):
    candidates = []
    for i in range(1, cand_count + 1):
        cand = contract.functions.getCandidate(election_id, i).call()
        if cand[3]: # If isActive
            candidates.append({"id": cand[0], "name": cand[1], "votes": cand[2]})
    return candidates

# --- STREAMLIT UI ---
st.set_page_config(page_title="Blockchain Voting Simulation", layout="centered")
init_db()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_id = None

# --- ROUTING & VIEWS ---
if not st.session_state.logged_in:
    st.title("🗳️ Decentralized Voting Portal")
    menu = st.radio("Navigate", ["Voter Login", "Voter Registration", "Admin Login"], horizontal=True)
    
    if menu == "Voter Registration":
        st.subheader("Register to Vote")
        reg_no = st.text_input("Registration Number")
        name = st.text_input("Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone Number")
        password = st.text_input("Password", type="password")
        
        if st.button("Register"):
            conn = sqlite3.connect('voters.db')
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                          (reg_no, name, email, phone, hash_password(password)))
                conn.commit()
                st.success("Registration Successful! Please navigate to Voter Login.")
            except sqlite3.IntegrityError:
                st.error("Registration Number already exists!")
            conn.close()
            
    elif menu == "Voter Login":
        st.subheader("Voter Login")
        reg_no = st.text_input("Registration Number")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            conn = sqlite3.connect('voters.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE reg_no=? AND password=?", (reg_no, hash_password(password)))
            user = c.fetchone()
            conn.close()
            
            if user:
                st.session_state.logged_in = True
                st.session_state.role = 'voter'
                st.session_state.user_id = reg_no
                st.rerun()
            else:
                st.error("Invalid Credentials")
                
    elif menu == "Admin Login":
        st.subheader("Admin Portal")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.session_state.role = 'admin'
                st.rerun()
            else:
                st.error("Invalid Admin Credentials")

else:
    # --- ADMIN DASHBOARD ---
    if st.session_state.role == 'admin':
        st.title("⚙️ Admin Dashboard")
        st.write("Manage multiple elections securely on the Ethereum blockchain.")
        
        tab1, tab2 = st.tabs(["Create Election", "Manage Candidates"])
        
        with tab1:
            st.subheader("Launch a New Election")
            new_election_name = st.text_input("Election Name")
            if st.button("Create Election"):
                with st.spinner("Writing to blockchain..."):
                    send_transaction(contract.functions.createElection(new_election_name))
                st.success(f"Election '{new_election_name}' created on the blockchain!")
                st.rerun()

        with tab2:
            st.subheader("Modify Existing Elections")
            elections = fetch_all_elections()
            
            if not elections:
                st.warning("No elections created yet.")
            else:
                selected_elec_name = st.selectbox("Select Election to Manage", [e["name"] for e in elections])
                selected_elec = next(e for e in elections if e["name"] == selected_elec_name)
                
                st.write(f"**Managing:** {selected_elec['name']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**Add Candidate**")
                    new_cand_name = st.text_input("New Candidate Name", key="add_name")
                    if st.button("Add", key="btn_add"):
                        with st.spinner("Processing..."):
                            send_transaction(contract.functions.addCandidate(selected_elec['id'], new_cand_name))
                        st.success("Candidate Added!")
                        st.rerun()
                
                candidates = fetch_active_candidates(selected_elec['id'], selected_elec['cand_count'])
                
                with col2:
                    st.markdown("**Edit Candidate**")
                    if candidates:
                        edit_cand_name = st.selectbox("Select Candidate to Edit", [c["name"] for c in candidates])
                        edit_cand_id = next(c["id"] for c in candidates if c["name"] == edit_cand_name)
                        updated_name = st.text_input("Updated Name", key="edit_name")
                        if st.button("Update", key="btn_edit"):
                            with st.spinner("Processing..."):
                                send_transaction(contract.functions.editCandidate(selected_elec['id'], edit_cand_id, updated_name))
                            st.success("Candidate Updated!")
                            st.rerun()
                    else:
                        st.info("No candidates to edit.")

                with col3:
                    st.markdown("**Delete Candidate**")
                    if candidates:
                        del_cand_name = st.selectbox("Select Candidate to Delete", [c["name"] for c in candidates])
                        del_cand_id = next(c["id"] for c in candidates if c["name"] == del_cand_name)
                        if st.button("Delete", key="btn_del"):
                            with st.spinner("Processing..."):
                                send_transaction(contract.functions.deleteCandidate(selected_elec['id'], del_cand_id))
                            st.success("Candidate Deleted!")
                            st.rerun()
                    else:
                        st.info("No candidates to delete.")
                        
                st.divider()
                st.markdown("### Current Results")
                for c in candidates:
                    st.write(f"ID: {c['id']} | Name: {c['name']} | Votes: {c['votes']}")

        st.divider()
        if st.button("Logout", type="primary"):
            st.session_state.clear()
            st.rerun()
            
    # --- VOTER BOOTH ---
    elif st.session_state.role == 'voter':
        st.title("🗳️ Secure Voting Booth")
        
        elections = fetch_all_elections()
        
        if not elections:
            st.warning("There are currently no active elections.")
        else:
            st.subheader("Select an Election")
            selected_elec_name = st.selectbox("Available Elections", [e["name"] for e in elections])
            selected_elec = next(e for e in elections if e["name"] == selected_elec_name)
            
            st.divider()
            
            try:
                # Check if user has already voted IN THIS SPECIFIC ELECTION
                has_voted = contract.functions.hasVoted(selected_elec['id'], st.session_state.user_id).call()
                
                if has_voted:
                    st.info(f"You have already cast your vote for '{selected_elec['name']}'. Blockchain ensures end-to-end verifiability and trust.")
                else:
                    candidates = fetch_active_candidates(selected_elec['id'], selected_elec['cand_count'])
                    
                    if not candidates:
                        st.warning("No candidates have been added to this election yet.")
                    else:
                        st.write("Select your candidate below. Your vote will be recorded securely as an immutable transaction.")
                        
                        selected_cand_name = st.radio("Candidates", [c["name"] for c in candidates])
                        selected_cand_id = next(c["id"] for c in candidates if c["name"] == selected_cand_name)
                        
                        if st.button("Cast Vote"):
                            with st.spinner("Processing transaction on Ethereum network..."):
                                send_transaction(contract.functions.vote(selected_elec['id'], selected_cand_id, st.session_state.user_id))
                            st.success("Vote securely recorded! Because voting and counting occur simultaneously, results are instantly available.")
                            st.rerun()
            except Exception as e:
                st.error("Error connecting to the blockchain network.")

        st.divider()
        if st.button("Logout", type="primary"):
            st.session_state.clear()
            st.rerun()
