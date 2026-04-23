import streamlit as st
import sqlite3
import hashlib
from web3 import Web3
import json

# --- BLOCKCHAIN CONFIGURATION ---
# Replace with your free Alchemy/Infura URL or local Ganache URL
RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/CFxXzoYXrLaFvVyBtt36G" 
CONTRACT_ADDRESS = "0xd17631ccC02a2e7e962B9Da98bEf8cd815BD9328"
# Paste the ABI you copied from Remix here (it's a long JSON list)
CONTRACT_ABI = json.loads('[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"string","name":"_name","type":"string"}],"name":"addCandidate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"admin","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"_name","type":"string"}],"name":"createElection","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"uint256","name":"_candidateId","type":"uint256"}],"name":"deleteCandidate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"uint256","name":"_candidateId","type":"uint256"},{"internalType":"string","name":"_newName","type":"string"}],"name":"editCandidate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"electionCandidates","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"name","type":"string"},{"internalType":"uint256","name":"voteCount","type":"uint256"},{"internalType":"bool","name":"isActive","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"elections","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"name","type":"string"},{"internalType":"uint256","name":"candidatesCount","type":"uint256"},{"internalType":"bool","name":"exists","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"electionsCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"uint256","name":"_candidateId","type":"uint256"}],"name":"getCandidate","outputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"string","name":"","type":"string"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"string","name":"","type":"string"}],"name":"hasVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_electionId","type":"uint256"},{"internalType":"uint256","name":"_candidateId","type":"uint256"},{"internalType":"string","name":"_voterId","type":"string"}],"name":"vote","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))
# NOTE: In a production app, NEVER hardcode private keys. Use st.secrets for Streamlit deployment.
# For this simulation, the admin private key is needed to sign transactions.
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
    """Helper to sign and send transactions to the blockchain"""
    nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)
    tx = func.build_transaction({
        'chainId': w3.eth.chain_id,
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=ADMIN_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)

# --- STREAMLIT UI ---
st.set_page_config(page_title="Blockchain Voting Simulation", layout="centered")
init_db()

# Session State Initialization
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
        st.write("Manage elections and candidates directly on the Ethereum blockchain.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. Set Election Name")
            election_name = st.text_input("New Election Name")
            if st.button("Update Election Name"):
                with st.spinner("Writing to blockchain..."):
                    send_transaction(contract.functions.setElectionName(election_name))
                st.success("Election name updated!")

        with col2:
            st.subheader("2. Add Candidate")
            candidate_name = st.text_input("Candidate Name")
            if st.button("Add Candidate"):
                with st.spinner("Writing to blockchain..."):
                    send_transaction(contract.functions.addCandidate(candidate_name))
                st.success(f"{candidate_name} added successfully!")

        st.divider()
        st.subheader("Current Election Status")
        try:
            current_name = contract.functions.electionName().call()
            st.write(f"**Active Election:** {current_name}")
            
            cand_count = contract.functions.candidatesCount().call()
            for i in range(1, cand_count + 1):
                cand = contract.functions.getCandidate(i).call()
                st.write(f"ID: {cand[0]} | Name: {cand[1]} | Votes: {cand[2]}")
        except Exception as e:
            st.warning("Could not fetch blockchain data. Check RPC URL and Contract Address.")

        if st.button("Logout", type="primary"):
            st.session_state.clear()
            st.rerun()
            
    # --- VOTER BOOTH ---
    elif st.session_state.role == 'voter':
        st.title("🗳️ Secure Voting Booth")
        
        try:
            current_name = contract.functions.electionName().call()
            st.subheader(f"Election: {current_name}")
            
            # Check if user has already voted
            has_voted = contract.functions.hasVoted(st.session_state.user_id).call()
            
            if has_voted:
                st.info("You have already cast your vote. Blockchain ensures end-to-end verifiability and trust[cite: 12].")
            else:
                cand_count = contract.functions.candidatesCount().call()
                candidates = []
                for i in range(1, cand_count + 1):
                    cand = contract.functions.getCandidate(i).call()
                    candidates.append({"id": cand[0], "name": cand[1]})
                
                if not candidates:
                    st.warning("No candidates available yet.")
                else:
                    st.write("Select your candidate below. Your vote will be recorded securely as an immutable transaction.")
                    
                    selected_cand_name = st.selectbox("Candidates", [c["name"] for c in candidates])
                    selected_id = next(c["id"] for c in candidates if c["name"] == selected_cand_name)
                    
                    if st.button("Cast Vote"):
                        with st.spinner("Processing transaction on Ethereum network..."):
                            # The app signs the transaction on behalf of the user to simulate the blockchain interaction
                            send_transaction(contract.functions.vote(selected_id, st.session_state.user_id))
                        st.success("Vote securely recorded! Because voting and counting occur simultaneously, results are instantly available[cite: 11, 38, 39].")
                        st.rerun()
        except Exception as e:
            st.error("Error connecting to the blockchain network.")

        st.divider()
        if st.button("Logout", type="primary"):
            st.session_state.clear()
            st.rerun()
