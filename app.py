import streamlit as st
import random
import time
import copy

# Constants for game elements
PLAYER_X = 'X'
PLAYER_O = 'O'
EMPTY_CELL = ''
BOARD_SIZE = 3

class TwistedTicTacToeStreamlit:
    def __init__(self):
        # Initialize session state variables only once per app load
        # This ensures persistence across Streamlit reruns
        if 'game_initialized' not in st.session_state:
            self._initialize_session_state()
            st.session_state.game_initialized = True

    def _initialize_session_state(self):
        """Initializes all necessary Streamlit session state variables to their default values."""
        st.session_state.current_screen = "twist_selection" # Controls which UI screen is displayed
        st.session_state.board = [[EMPTY_CELL for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)] # The game board
        st.session_state.current_player = PLAYER_X # 'X' always starts
        st.session_state.game_active = False # True when a game is in progress
        st.session_state.undo_mode = False # For 'Tic-Tac-Undo' twist
        st.session_state.evolve_marks = {} # Stores mark levels for 'Evolve Tic-Tac-Toe': {(row, col): level}
        st.session_state.player_abilities = { # Stores remaining ability uses for 'Tic-Tac-Toe with Abilities'
            PLAYER_X: {'swap': 1, 'block': 1, 'remove': 1},
            PLAYER_O: {'swap': 1, 'block': 1, 'remove': 1}
        }
        st.session_state.blocked_line = None # Stores a blocked winning line for 'Block' ability
        st.session_state.last_placed_mark_coords = None # For 'Memory Challenge' (not fully implemented in Streamlit)
        st.session_state.turn_time_limit = 10 # Seconds for 'Sudden Death Tic-Tac-Toe'
        st.session_state.turn_start_time = 0 # Timestamp when current turn started
        st.session_state.selected_twists = self._get_default_twists() # Dictionary of selected twists
        st.session_state.game_mode = "friend" # "friend" or "bot"
        st.session_state.bot_difficulty = "basic" # "basic" or "smart"
        st.session_state.bot_enabled = False # True if playing against the bot
        st.session_state.ability_mode = None # Stores the active ability type if any ('swap', 'block', 'remove')
        st.session_state.swap_first_click = None # Stores first selected cell for 'Swap' ability
        # board_history stores tuples: (board_state, evolve_marks_state) just before a player's move
        st.session_state.board_history = []
        st.session_state.game_message = "" # Message displayed to the user
        # For 'Memory Challenge': True means all marks are revealed, False means opponent's marks are hidden
        st.session_state.reveal_all_memory_marks = False
        st.session_state.last_board_shift_turn = 0 # Tracks turns for 'Board Shift Tic-Tac-Toe'
        st.session_state.bot_move_pending = False # Flag to trigger bot move on next Streamlit rerun

    def _get_default_twists(self):
        """Returns a dictionary of all possible twists with their default (off) state."""
        return {
            "Tic-Tac-Undo": False,
            "Gravity Tic-Tac-Toe": False,
            "Sudden Death Tic-Tac-Toe": False,
            "Evolve Tic-Tac-Toe": False,
            "Tic-Tac-Toe with Abilities": False,
            "Board Shift Tic-Tac-Toe": False,
            "Memory Challenge": False
        }

    def set_current_screen(self, screen_name):
        """Sets the current screen to be displayed."""
        st.session_state.current_screen = screen_name

    def display_twist_selection_screen(self):
        """Renders the initial screen for selecting game mode and twists."""
        st.title("Twisted Tic-Tac-Toe")
        st.header("Select Game Mode:")

        # Game Mode selection using radio buttons
        current_game_mode_index = 0 if st.session_state.game_mode == "friend" else 1
        new_game_mode_label = st.radio("Mode", ["Play with Friend", "Play with Computer"],
                                       index=current_game_mode_index, horizontal=True, key="game_mode_radio_main")
        st.session_state.game_mode = "friend" if new_game_mode_label == "Play with Friend" else "bot"

        # Difficulty selection is shown only if "Play with Computer" is selected
        if st.session_state.game_mode == "bot":
            st.subheader("Select Difficulty:")
            current_bot_difficulty_index = 0 if st.session_state.bot_difficulty == "basic" else 1
            new_bot_difficulty_label = st.radio("Difficulty", ["Basic Bot", "Smart Bot"],
                                                index=current_bot_difficulty_index, horizontal=True, key="bot_difficulty_radio_main")
            st.session_state.bot_difficulty = "basic" if new_bot_difficulty_label == "Basic Bot" else "smart"
        
        st.markdown("---")
        st.header("Select Game Twists:")

        # Detailed descriptions for each twist
        twists_info = {
            "Tic-Tac-Undo": "Players can undo their last mark.",
            "Gravity Tic-Tac-Toe": "Marks fall to the lowest available spot in a column.",
            "Sudden Death Tic-Tac-Toe": "Players have a limited time per turn.",
            "Evolve Tic-Tac-Toe": "Marks evolve (1, 2, 3) and higher numbers win.",
            "Tic-Tac-Toe with Abilities": "Players get special abilities (Swap, Block, Remove).",
            "Board Shift Tic-Tac-Toe": "The board shifts after 5 turns.",
            "Memory Challenge": "Opponent's entries are hidden, revealed briefly on certain actions (e.g., ability use, end of game)."
        }

        # Checkboxes for selecting game twists
        for twist_name, twist_desc in twists_info.items():
            st.session_state.selected_twists[twist_name] = st.checkbox(
                f"**{twist_name}** - {twist_desc}",
                value=st.session_state.selected_twists[twist_name], # Use current session state value
                key=f"twist_checkbox_{twist_name}" # Unique key for each checkbox
            )

        st.markdown("---")
        # Start Game button
        if st.button("Start Game", key="start_game_button", help="Click to start the game with selected twists."):
            if not any(st.session_state.selected_twists.values()):
                st.info("You haven't selected any twists. Playing a standard Tic-Tac-Toe game.")
            self._start_game() # Initialize game state
            self.set_current_screen("game_board") # Change to game board screen
            st.rerun() # Force a rerun to display the game board

    def _start_game(self):
        """Initializes all game-related state for a new game based on selected twists."""
        self._reset_game_state_for_new_game() # Reset board, player, etc.
        st.session_state.game_active = True
        st.session_state.bot_enabled = (st.session_state.game_mode == "bot")
        st.session_state.game_message = f"Player {st.session_state.current_player}'s turn."

        if st.session_state.selected_twists["Sudden Death Tic-Tac-Toe"]:
            st.session_state.turn_start_time = time.time() # Start timer for the first turn
        
        # If bot is enabled and it's Player O's turn (as X starts), flag for bot move
        if st.session_state.bot_enabled and st.session_state.current_player == PLAYER_O:
            st.session_state.bot_move_pending = True # Trigger bot move on the next rerun

    def _reset_game_state_for_new_game(self):
        """Resets specific game state variables for a fresh game round."""
        st.session_state.board = [[EMPTY_CELL for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        st.session_state.current_player = PLAYER_X
        st.session_state.game_active = True
        st.session_state.undo_mode = False
        st.session_state.evolve_marks = {}
        st.session_state.player_abilities = {
            PLAYER_X: {'swap': 1, 'block': 1, 'remove': 1},
            PLAYER_O: {'swap': 1, 'block': 1, 'remove': 1}
        }
        st.session_state.blocked_line = None
        st.session_state.last_placed_mark_coords = None
        st.session_state.turn_time_limit = 10
        st.session_state.turn_start_time = time.time()
        st.session_state.game_message = ""
        st.session_state.ability_mode = None
        st.session_state.swap_first_click = None
        st.session_state.board_history = [] # Clear history for a new game
        st.session_state.reveal_all_memory_marks = True # Reveal all marks briefly at the start of a new game
        st.session_state.last_board_shift_turn = 0
        st.session_state.bot_move_pending = False

    def display_game_board_screen(self):
        """Renders the main game board screen."""
        st.title("Twisted Tic-Tac-Toe Game")

        # Handle pending bot moves. This pattern ensures bot moves are processed after UI updates
        # and before the user can interact again.
        if st.session_state.bot_enabled and st.session_state.current_player == PLAYER_O and st.session_state.game_active and st.session_state.bot_move_pending:
            st.session_state.game_message = "Bot is thinking..."
            st.info("Bot is thinking...") # Provide immediate visual feedback
            time.sleep(0.5) # Simulate thinking time for bot
            self._bot_move() # Execute bot's move
            st.session_state.bot_move_pending = False # Reset the flag
            st.rerun() # Force a rerun to display the board after bot's move

        # Placeholder for dynamic status messages
        status_message_placeholder = st.empty()
        status_message_placeholder.markdown(f"**{st.session_state.game_message}**")

        # Display timer for Sudden Death twist
        if st.session_state.selected_twists["Sudden Death Tic-Tac-Toe"] and st.session_state.game_active:
            elapsed_time = time.time() - st.session_state.turn_start_time
            remaining_time = max(0, int(st.session_state.turn_time_limit - elapsed_time))
            st.markdown(f"Time: {remaining_time}s")
            # Check for timeout and end game if time runs out
            if remaining_time <= 0 and st.session_state.game_active:
                self._end_game(f"Player {st.session_state.current_player} ran out of time! Player {PLAYER_O if st.session_state.current_player == PLAYER_X else PLAYER_X} wins!")
                st.rerun()

        # Render the Tic-Tac-Toe board
        self._render_board()

        # Render control buttons (Reset, Change Twists, Undo)
        self._render_control_buttons()
        # Render ability buttons (Swap, Block, Remove)
        self._render_ability_buttons()
        

    def _render_board(self):
        """Renders the Tic-Tac-Toe board using Streamlit columns and buttons, applying custom CSS."""
        with st.container():
            # Inject custom CSS for button styling (size, shape, colors)
            st.markdown("""
            <style>
                /* Style for all Streamlit buttons */
                .stButton > button {
                    font-size: 3em !important; /* Make X/O marks larger */
                    width: 100px; /* Fixed width for uniform cells */
                    height: 100px; /* Fixed height for uniform cells */
                    border-radius: 10px; /* Rounded corners */
                    background-color: #ECEFF1; /* Light gray background */
                    color: #212121; /* Default dark gray text */
                    border: 2px solid #90A4AE; /* Border color */
                    margin: 5px; /* Spacing between cells */
                    display: flex; /* Use flexbox for centering content */
                    justify-content: center; /* Center horizontally */
                    align-items: center; /* Center vertically */
                    cursor: pointer; /* Pointer cursor for clickable cells */
                    transition: background-color 0.2s ease; /* Smooth hover effect */
                }
                /* Hover effect for clickable buttons */
                .stButton > button:hover:not(:disabled) {
                    background-color: #CFD8DC; /* Slightly darker gray on hover */
                }
                /* Style for disabled buttons */
                .stButton > button:disabled {
                    opacity: 0.6; /* Dim disabled buttons */
                    cursor: not-allowed; /* No-go cursor */
                }
                /* Specific colors for X and O marks */
                .x-mark { color: #E91E63; } /* Red-ish for X */
                .o-mark { color: #2196F3; } /* Blue-ish for O */
            </style>
            """, unsafe_allow_html=True) # Allow Streamlit to render custom HTML/CSS

            # Create a 3x3 grid using Streamlit columns
            for r in range(BOARD_SIZE):
                board_row_cols = st.columns(BOARD_SIZE) # Create columns for each row
                for c in range(BOARD_SIZE):
                    with board_row_cols[c]: # Place content within each column
                        mark_on_board = st.session_state.board[r][c]
                        mark_display = mark_on_board
                        
                        # Apply 'Evolve Tic-Tac-Toe' display logic
                        if st.session_state.selected_twists["Evolve Tic-Tac-Toe"] and (r,c) in st.session_state.evolve_marks:
                            if mark_on_board != EMPTY_CELL: # Only show level if a mark exists
                                mark_display += str(st.session_state.evolve_marks[(r,c)])

                        # Apply 'Memory Challenge' visibility logic
                        if st.session_state.selected_twists["Memory Challenge"]:
                            # If not set to reveal all and it's an opponent's mark, hide it
                            if not st.session_state.reveal_all_memory_marks and mark_on_board != st.session_state.current_player:
                                mark_display = "" # Hide opponent's mark
                            # If it's the current player's mark and Evolve is on, ensure level is shown
                            elif mark_on_board == st.session_state.current_player and st.session_state.selected_twists["Evolve Tic-Tac-Toe"] and (r,c) in st.session_state.evolve_marks:
                                mark_display = mark_on_board + str(st.session_state.evolve_marks[(r,c)])

                        # Ensure button has text, even if empty, to maintain size
                        button_text = mark_display if mark_display else " "
                        
                        # Determine if the button should be disabled
                        button_disabled = not st.session_state.game_active # Disable if game not active
                        # Disable human clicks during bot's turn
                        if st.session_state.bot_enabled and st.session_state.current_player == PLAYER_O:
                            button_disabled = True
                        
                        # Special handling for ability mode clicks: enable all cells temporarily
                        if st.session_state.ability_mode:
                            button_disabled = False # Enable clicks for ability selection
                            # For swap, disable re-clicking the first chosen cell
                            if st.session_state.ability_mode == 'swap' and st.session_state.swap_first_click == (r,c):
                                button_disabled = True
                            # For remove, disable clicking an empty cell
                            if st.session_state.ability_mode == 'remove' and st.session_state.board[r][c] == EMPTY_CELL:
                                button_disabled = True
                            # For block, any cell is valid, logic handles if no lines to block

                        # Apply color class based on player mark for styling
                        mark_class = ""
                        if mark_on_board == PLAYER_X:
                            mark_class = "x-mark"
                        elif mark_on_board == PLAYER_O:
                            mark_class = "o-mark"

                        # Create the button with dynamic content and styling
                        if st.button(button_text, key=f"cell_{r}_{c}", use_container_width=True, disabled=button_disabled)
,
                                     use_container_width=True, disabled=button_disabled, unsafe_allow_html=True):
                            self._handle_click(r, c) # Handle the click event
                            st.rerun() # Force a rerun to update the UI

    def _render_control_buttons(self):
        """Renders general game control buttons like 'Undo', 'Reset Game', and 'Change Twists'."""
        st.markdown("---")
        control_cols = st.columns(3) # Create three columns for the buttons
        with control_cols[0]:
            # 'Tic-Tac-Undo' button logic
            if st.session_state.selected_twists["Tic-Tac-Undo"]:
                button_text = "Toggle Undo Mode (Active)" if st.session_state.undo_mode else "Toggle Undo Mode (Inactive)"
                # Disable undo button if it's bot's turn or an ability is active
                undo_disabled = (st.session_state.bot_enabled and st.session_state.current_player == PLAYER_O) or \
                                st.session_state.ability_mode is not None
                if st.button(button_text, key="undo_button", help="Toggle undo mode to remove your mark.",
                             disabled=undo_disabled):
                    self._toggle_undo_mode() # Toggle undo mode
                    st.rerun() # Force rerun to update UI

        with control_cols[1]:
            # 'Reset Game' button
            if st.button("Reset Game", key="reset_game_button", help="Start a new game with the same twists."):
                self._reset_game_state_for_new_game() # Reset game state to start a new round
                st.rerun() # Force rerun

        with control_cols[2]:
            # 'Change Twists' button
            if st.button("Change Twists", key="change_twists_button", help="Go back to the twist selection screen."):
                self.set_current_screen("twist_selection") # Change screen
                self._initialize_session_state() # Fully re-initialize all session state
                st.rerun() # Force rerun

    def _render_ability_buttons(self):
        """Renders ability buttons (Swap, Block, Remove) if the 'Abilities' twist is active."""
        if st.session_state.selected_twists["Tic-Tac-Toe with Abilities"]:
            st.markdown("---")
            st.subheader("Abilities:")
            ability_cols = st.columns(3) # Create three columns for ability buttons
            abilities_info = {
                'swap': "Swap", 'block': "Block", 'remove': "Remove"
            }
            for i, (ability_type, btn_text) in enumerate(abilities_info.items()):
                with ability_cols[i]:
                    count = st.session_state.player_abilities[st.session_state.current_player][ability_type] # Get remaining uses
                    button_label = f"{btn_text} ({count})"
                    
                    # Disable ability button if no uses left, game not active, or another ability is active
                    button_disabled = (count <= 0 or not st.session_state.game_active or st.session_state.ability_mode is not None)
                    # Disable human abilities during bot's turn
                    if st.session_state.bot_enabled and st.session_state.current_player == PLAYER_O:
                        button_disabled = True

                    if st.button(button_label, key=f"ability_{ability_type}_btn", disabled=button_disabled):
                        self._use_ability(ability_type) # Initiate ability use
                        st.rerun() # Force rerun to update status and enable ability clicks

    def _reset_game(self):
        """Resets the entire application to the twist selection screen by re-initializing session state."""
        self._initialize_session_state()
        st.rerun()

    def _toggle_undo_mode(self):
        """Toggles the 'Tic-Tac-Undo' mode, allowing players to remove their own marks."""
        st.session_state.undo_mode = not st.session_state.undo_mode
        if st.session_state.undo_mode:
            st.session_state.game_message = "Undo Mode Active: Click on your mark to remove it."
        else:
            st.session_state.game_message = f"Player {st.session_state.current_player}'s turn."

        # If Memory Challenge is on and no ability is active, hide opponent's marks
        if st.session_state.selected_twists["Memory Challenge"] and st.session_state.ability_mode is None:
            st.session_state.reveal_all_memory_marks = False

    def _handle_click(self, r, c):
        """Handles a click event on a board cell."""
        if not st.session_state.game_active:
            st.session_state.game_message = "Game is not active. Start a new game."
            return

        # If Memory Challenge is on, temporarily reveal all marks for the human player's decision
        if st.session_state.selected_twists["Memory Challenge"]:
            st.session_state.reveal_all_memory_marks = True
        
        # If an ability is active, delegate to the ability-specific handler
        if st.session_state.ability_mode:
            self._handle_ability_click(r, c)
            return # Rerun will be handled by _handle_ability_click

        # Handle 'Tic-Tac-Undo' mode logic
        if st.session_state.selected_twists["Tic-Tac-Undo"] and st.session_state.undo_mode:
            # Allow removing any of the current player's marks
            if st.session_state.board[r][c] == st.session_state.current_player:
                # Store current board state in history before modification for future undo
                history_entry = (copy.deepcopy(st.session_state.board), copy.deepcopy(st.session_state.evolve_marks))
                st.session_state.board_history.append(history_entry)

                st.session_state.board[r][c] = EMPTY_CELL # Remove the mark
                # Remove evolve mark data if it exists
                if (r,c) in st.session_state.evolve_marks:
                    del st.session_state.evolve_marks[(r,c)]
                st.session_state.game_message = "Mark removed!"
                self._switch_player_and_end_turn_actions() # Switch player and handle end-turn actions
            else:
                st.session_state.game_message = "You can only undo your own marks in undo mode!"
        else: # Handle regular mark placement (includes 'Gravity Tic-Tac-Toe')
            if st.session_state.selected_twists["Gravity Tic-Tac-Toe"]:
                actual_row = self._get_gravity_placement(st.session_state.board, c)
                if actual_row is not None:
                    # Store current board state in history before modification
                    history_entry = (copy.deepcopy(st.session_state.board), copy.deepcopy(st.session_state.evolve_marks))
                    st.session_state.board_history.append(history_entry)
                    self._place_mark(actual_row, c) # Place mark at the lowest available row
                else:
                    st.session_state.game_message = "Column is full! Try another."
            else: # Standard Tic-Tac-Toe placement
                if st.session_state.board[r][c] == EMPTY_CELL:
                    # Store current board state in history before modification
                    history_entry = (copy.deepcopy(st.session_state.board), copy.deepcopy(st.session_state.evolve_marks))
                    st.session_state.board_history.append(history_entry)
                    self._place_mark(r, c) # Place mark at the clicked cell
                else:
                    st.session_state.game_message = "This spot is already taken! Choose an empty one."
        
        # A rerun is generally triggered by the button click itself, or by _place_mark/_switch_player_and_end_turn_actions

    def _place_mark(self, r, c):
        """Places a mark on the board at the specified (r, c) coordinates, applying 'Evolve' twist if active."""
        if st.session_state.selected_twists["Evolve Tic-Tac-Toe"]:
            current_level = st.session_state.evolve_marks.get((r,c), 0) # Get current level, default to 0
            if current_level >= 3: # Max evolution level is 3
                st.session_state.game_message = "This spot has reached max evolution level!"
                return # Do not place mark if max level reached
            new_level = current_level + 1
            st.session_state.board[r][c] = st.session_state.current_player
            st.session_state.evolve_marks[(r,c)] = new_level
        else:
            st.session_state.board[r][c] = st.session_state.current_player
        
        st.session_state.last_placed_mark_coords = (r, c) # Record for Memory Challenge (if active)

        # Check for win or draw after placing the mark
        if self._check_win(st.session_state.board, st.session_state.evolve_marks, st.session_state.current_player):
            self._end_game(f"Player {st.session_state.current_player} wins!")
        elif self._check_draw(st.session_state.board):
            self._end_game("It's a draw!")
        else:
            self._switch_player_and_end_turn_actions() # Proceed to next player's turn and end-turn actions

    def _switch_player_and_end_turn_actions(self):
        """Handles switching players and other actions that occur at the end of a turn (e.g., board shift, memory hide)."""
        # If 'Memory Challenge' is active, hide opponent's marks for the next player's turn
        if st.session_state.selected_twists["Memory Challenge"]:
            st.session_state.reveal_all_memory_marks = False

        self._switch_player() # Switch the current player

        # Apply 'Board Shift Tic-Tac-Toe' twist logic
        if st.session_state.selected_twists["Board Shift Tic-Tac-Toe"]:
            filled_cells = sum(1 for row in st.session_state.board for cell in row if cell != EMPTY_CELL)
            # Shift board every 5 moves (after 5th, 10th, 15th move, etc.)
            if filled_cells > 0 and (filled_cells - st.session_state.last_board_shift_turn) % 5 == 0:
                self._shift_board()
                st.session_state.last_board_shift_turn = filled_cells # Update last shift turn
                st.session_state.game_message += "\nBoard has shifted!" # Add message to current status

        # If bot is enabled and it's the bot's turn, set flag to trigger bot move on next rerun
        if st.session_state.bot_enabled and st.session_state.current_player == PLAYER_O:
            st.session_state.bot_move_pending = True

    def _get_gravity_placement(self, board_state, col):
        """
        Finds the lowest empty row in a given column for 'Gravity Tic-Tac-Toe' twist.
        Operates on a given board_state, not necessarily the session_state.board.
        """
        for r in range(BOARD_SIZE - 1, -1, -1): # Check from bottom row upwards
            if board_state[r][col] == EMPTY_CELL:
                return r # Return the row index
        return None # Column is full

    def _check_win(self, board_state, evolve_marks_state, player):
        """
        Checks for win conditions for a given player on a given board state,
        adapting for 'Evolve Tic-Tac-Toe' and 'Block' ability.
        """
        winning_lines_found = []

        # Check rows for 3 in a row
        for r in range(BOARD_SIZE):
            if all(board_state[r][c] == player for c in range(BOARD_SIZE)):
                winning_lines_found.append(((r,0),(r,1),(r,2)))
        # Check columns for 3 in a row
        for c in range(BOARD_SIZE):
            if all(board_state[r][c] == player for r in range(BOARD_SIZE)):
                winning_lines_found.append(((0,c),(1,c),(2,c)))
        # Check main diagonal
        if all(board_state[i][i] == player for i in range(BOARD_SIZE)):
            winning_lines_found.append(((0,0),(1,1),(2,2)))
        # Check anti-diagonal
        if all(board_state[i][BOARD_SIZE-1-i] == player for i in range(BOARD_SIZE)):
            winning_lines_found.append(((0,2),(1,1),(2,0)))

        # If 'Evolve Tic-Tac-Toe' is active, filter winning lines to ensure marks are evolved
        if st.session_state.selected_twists["Evolve Tic-Tac-Toe"]:
            evolved_winning_lines = []
            for line in winning_lines_found:
                # All marks in the line must have an evolved level (> 0) to count as a win
                if all(evolve_marks_state.get(coord, 0) > 0 for coord in line):
                    evolved_winning_lines.append(line)
            winning_lines_found = evolved_winning_lines # Only consider evolved lines as wins

        # If 'Block' ability is active, check if the winning line is currently blocked
        # This check applies only to the *actual* game board, not during minimax simulations.
        is_actual_game_board = (board_state is st.session_state.board)
        if st.session_state.selected_twists["Tic-Tac-Toe with Abilities"] and st.session_state.blocked_line and is_actual_game_board:
            for line in winning_lines_found:
                # Convert line coordinates to sets for order-independent comparison
                if set(line) == set(st.session_state.blocked_line):
                    st.session_state.game_message = f"Player {player}'s winning line was blocked!"
                    st.session_state.blocked_line = None # Clear the block after it's used
                    return False # No win this turn due to block
        
        return len(winning_lines_found) > 0 # Return True if any valid winning line exists

    def _check_draw(self, board_state):
        """Checks if the game is a draw on a given board state (no empty cells)."""
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board_state[r][c] == EMPTY_CELL:
                    return False # Found an empty spot, not a draw yet
        return True # Board is full, it's a draw

    def _end_game(self, message):
        """Ends the game, displays a final message, and provides options to play again or change twists."""
        st.session_state.game_active = False # Deactivate the game
        st.session_state.game_message = message # Set final message
        st.session_state.ability_mode = None # Clear any active ability mode
        st.session_state.swap_first_click = None # Clear any pending swap selections
        st.session_state.reveal_all_memory_marks = True # Reveal all marks at game end for full view
        st.session_state.bot_move_pending = False # Stop any pending bot moves

        # Display game over options
        st.subheader("Game Over!")
        st.write(message)
        col1, col2 = st.columns(2) # Create two columns for buttons
        with col1:
            if st.button("Play Again", key="play_again_button_end", help="Start a new game with the same twists."):
                self._reset_game_state_for_new_game() # Reset game state
                st.rerun() # Force rerun
        with col2:
            if st.button("Change Twists", key="change_twists_button_end", help="Go back to the twist selection screen."):
                self.set_current_screen("twist_selection") # Change screen
                self._initialize_session_state() # Fully reset all session state
                st.rerun() # Force rerun

    def _switch_player(self):
        """Switches the current player and resets the turn timer for 'Sudden Death'."""
        st.session_state.current_player = PLAYER_O if st.session_state.current_player == PLAYER_X else PLAYER_X
        st.session_state.game_message = f"Player {st.session_state.current_player}'s turn."
        if st.session_state.selected_twists["Sudden Death Tic-Tac-Toe"]:
            st.session_state.turn_start_time = time.time() # Reset timer for the new player

    # --- 'Board Shift' Twist Implementation ---
    def _shift_board(self):
        """Shifts the board content (rows move up, top row is lost, new empty row at bottom)."""
        st.session_state.game_message = "The board is shifting!" # This message will be appended
        new_board = [[EMPTY_CELL for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        new_evolve_marks = {} # Also shift evolve marks accordingly

        # Shift all rows up by one. The top row is lost, and a new empty row appears at the bottom.
        for r in range(1, BOARD_SIZE): # Start from the second row (index 1)
            for c in range(BOARD_SIZE):
                new_board[r-1][c] = st.session_state.board[r][c] # Move current row 'r' to 'r-1'
                if (r,c) in st.session_state.evolve_marks:
                    new_evolve_marks[(r-1,c)] = st.session_state.evolve_marks[(r,c)] # Move evolve mark

        st.session_state.board = new_board # Update the main board
        st.session_state.evolve_marks = new_evolve_marks # Update evolve marks
        # Streamlit will automatically re-render the board on the next rerun

    # --- 'Abilities' Twist Implementation ---
    def _use_ability(self, ability_type):
        """Initiates the use of a player ability (e.g., 'swap', 'block', 'remove')."""
        if st.session_state.player_abilities[st.session_state.current_player][ability_type] <= 0:
            st.session_state.game_message = "You don't have any uses left for this ability!"
            return

        st.session_state.ability_mode = ability_type # Set the active ability mode
        st.session_state.game_message = f"Ability Mode: Click on the board to use '{ability_type.capitalize()}' ability!"
        
        # If 'Memory Challenge' is active, reveal all marks for strategic ability use
        if st.session_state.selected_twists["Memory Challenge"]:
            st.session_state.reveal_all_memory_marks = True

    def _handle_ability_click(self, r, c):
        """Handles a click on the board when an ability is active."""
        ability_type = st.session_state.ability_mode
        performed_action = False # Flag to indicate if an ability action was successfully performed

        if ability_type == 'swap':
            if st.session_state.swap_first_click is None:
                st.session_state.swap_first_click = (r, c) # Store the first clicked cell
                st.session_state.game_message = f"Swap: Select second cell to swap with ({r+1},{c+1})."
            else:
                r1, c1 = st.session_state.swap_first_click
                r2, c2 = (r, c)

                if (r1, c1) == (r2, c2):
                    st.session_state.game_message = "Cannot swap a cell with itself!"
                    self._reset_ability_mode() # Reset ability mode and exit
                    return

                # Store current state in history before performing the swap
                history_entry = (copy.deepcopy(st.session_state.board), copy.deepcopy(st.session_state.evolve_marks))
                st.session_state.board_history.append(history_entry)

                # Perform the actual swap of marks and evolve levels
                temp_mark = st.session_state.board[r1][c1]
                temp_evolve = st.session_state.evolve_marks.get((r1,c1), None)

                st.session_state.board[r1][c1] = st.session_state.board[r2][c2]
                st.session_state.evolve_marks[(r1,c1)] = st.session_state.evolve_marks.get((r2,c2), None)
                # Clean up evolve_marks if a cell becomes empty or loses its evolve status
                if (r1,c1) in st.session_state.evolve_marks and st.session_state.evolve_marks[(r1,c1)] is None:
                    del st.session_state.evolve_marks[(r1,c1)]

                st.session_state.board[r2][c2] = temp_mark
                st.session_state.evolve_marks[(r2,c2)] = temp_evolve
                if (r2,c2) in st.session_state.evolve_marks and st.session_state.evolve_marks[(r2,c2)] is None:
                    del st.session_state.evolve_marks[(r2,c2)]

                st.session_state.player_abilities[st.session_state.current_player]['swap'] -= 1 # Decrement ability use
                st.session_state.game_message = "Marks swapped!"
                performed_action = True # Indicate successful action

        elif ability_type == 'block':
            st.session_state.player_abilities[st.session_state.current_player]['block'] -= 1
            opponent = PLAYER_O if st.session_state.current_player == PLAYER_X else PLAYER_X
            potential_lines = self._get_all_potential_winning_lines(opponent) # Get all potential winning lines for opponent
            if potential_lines:
                st.session_state.blocked_line = random.choice(potential_lines) # Randomly block one line
                st.session_state.game_message = f"Player {st.session_state.current_player} blocked a random line for the next turn!"
            else:
                st.session_state.game_message = f"Player {st.session_state.current_player} used Block, but no immediate lines to block."
            performed_action = True

        elif ability_type == 'remove':
            if st.session_state.board[r][c] != EMPTY_CELL: # Can only remove a non-empty spot
                # Store current state in history before performing removal
                history_entry = (copy.deepcopy(st.session_state.board), copy.deepcopy(st.session_state.evolve_marks))
                st.session_state.board_history.append(history_entry)

                original_owner = st.session_state.board[r][c]
                st.session_state.board[r][c] = EMPTY_CELL # Remove the mark
                # Remove evolve mark data if it exists
                if (r,c) in st.session_state.evolve_marks:
                    del st.session_state.evolve_marks[(r,c)]
                st.session_state.player_abilities[st.session_state.current_player]['remove'] -= 1 # Decrement ability use
                st.session_state.game_message = f"Mark of player {original_owner} at ({r+1},{c+1}) removed!"
                performed_action = True
            else:
                st.session_state.game_message = "Cannot remove an empty spot!"
                # performed_action remains False, so turn will not switch

        if performed_action:
            self._reset_ability_mode() # Reset ability mode
            self._switch_player_and_end_turn_actions() # Switch player and handle end-turn actions
        else:
            self._reset_ability_mode() # If no action (e.g., clicked empty for remove), still reset mode
        st.rerun() # Force a rerun to update the UI

    def _reset_ability_mode(self):
        """Resets the active ability mode and related temporary states."""
        st.session_state.ability_mode = None
        st.session_state.swap_first_click = None
        # If 'Memory Challenge' is active, hide opponent's marks when ability mode ends
        if st.session_state.selected_twists["Memory Challenge"]:
            st.session_state.reveal_all_memory_marks = False

    def _get_all_potential_winning_lines(self, player):
        """Helper function to get all possible 3-in-a-row lines on the board."""
        lines = []
        # Rows
        for r in range(BOARD_SIZE):
            lines.append(((r,0),(r,1),(r,2)))
        # Columns
        for c in range(BOARD_SIZE):
            lines.append(((0,c),(1,c),(2,c)))
        # Diagonals
        lines.append(((0,0),(1,1),(2,2)))
        lines.append(((0,2),(1,1),(2,0)))
        return lines

    # --- Bot Logic Implementation ---
    def _bot_move(self):
        """Determines and executes the bot's move based on difficulty."""
        if not st.session_state.game_active:
            return

        # Temporarily reveal all marks for the bot's internal decision making
        original_reveal_state = st.session_state.reveal_all_memory_marks
        st.session_state.reveal_all_memory_marks = True # Bot needs to see the full board

        # Store current board state in history before bot makes its move (for undo)
        history_entry = (copy.deepcopy(st.session_state.board), copy.deepcopy(st.session_state.evolve_marks))
        st.session_state.board_history.append(history_entry)

        if st.session_state.bot_difficulty == "basic":
            self._basic_bot_move()
        else: # Smart Bot
            self._smart_bot_move()
        
        # Restore the original memory challenge reveal state after the bot's turn
        st.session_state.reveal_all_memory_marks = original_reveal_state

    def _basic_bot_move(self):
        """Basic bot logic: chooses a random empty cell."""
        available = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if st.session_state.board[r][c] == EMPTY_CELL]
        if available:
            if st.session_state.selected_twists["Gravity Tic-Tac-Toe"]:
                valid_gravity_moves = []
                for _, c in available: # Iterate columns to find valid gravity placements
                    actual_r = self._get_gravity_placement(st.session_state.board, c)
                    if actual_r is not None and (actual_r, c) not in valid_gravity_moves:
                        valid_gravity_moves.append((actual_r, c))
                
                if valid_gravity_moves:
                    r, c = random.choice(valid_gravity_moves)
                    self._place_mark(r, c)
                else:
                    st.session_state.game_message = "Basic bot couldn't find a gravity move. (Unexpected state if spots are available)"
            else:
                r, c = random.choice(available)
                self._place_mark(r, c)

    def _smart_bot_move(self):
        """Smart bot logic: uses Minimax algorithm to find the optimal move."""
        best_score = -float('inf')
        move = None
        
        # Iterate through all possible cells to find the best move
        for r_iter in range(BOARD_SIZE):
            for c_iter in range(BOARD_SIZE):
                # Create deep copies of board state for minimax simulation
                temp_board = copy.deepcopy(st.session_state.board)
                temp_evolve_marks = copy.deepcopy(st.session_state.evolve_marks)
                
                current_r, current_c = r_iter, c_iter
                # Apply 'Gravity Tic-Tac-Toe' for minimax consideration
                if st.session_state.selected_twists["Gravity Tic-Tac-Toe"]:
                    actual_r = self._get_gravity_placement(temp_board, c_iter)
                    if actual_r is None: # Column is full, skip this move
                        continue
                    current_r = actual_r # The actual row where the mark would land
                
                if temp_board[current_r][current_c] == EMPTY_CELL:
                    # Make the move on the temporary board for simulation
                    temp_board[current_r][current_c] = PLAYER_O # Bot's move
                    if st.session_state.selected_twists["Evolve Tic-Tac-Toe"]:
                        temp_evolve_marks[(current_r, current_c)] = temp_evolve_marks.get((current_r, current_c), 0) + 1

                    # Call minimax to evaluate this move. `False` indicates it's now Minimizing Player's turn (Human 'X')
                    score = self._minimax(temp_board, temp_evolve_marks, 0, False)
                    
                    if score > best_score:
                        best_score = score
                        move = (current_r, current_c) # Store the best move found so far
        
        if move:
            self._place_mark(*move) # Execute the best move
        else:
            # Fallback to basic bot if smart bot can't find an optimal move (e.g., board full)
            st.session_state.game_message = "Smart bot found no optimal moves, making a random move."
            self._basic_bot_move()

    def _minimax(self, board_state, evolve_marks_state, depth, is_max):
        """
        Minimax algorithm to find the best move for the bot.
        This function operates on *passed* board_state and evolve_marks_state,
        ensuring it doesn't modify the main game's session_state during simulation.
        """
        # Base cases: Check for win/draw on the current simulated board state
        if self._check_win(board_state, evolve_marks_state, PLAYER_O): # If O wins in this state
            return 1 # Maximize score for O
        if self._check_win(board_state, evolve_marks_state, PLAYER_X): # If X wins in this state
            return -1 # Minimize score for O
        if self._check_draw(board_state): # If it's a draw
            return 0 # Neutral score

        # Limit search depth to prevent excessive computation, especially in a web environment
        if depth >= 5: # Tunable depth limit (deeper means smarter but slower)
            return 0 # Return neutral score if depth limit is reached

        if is_max: # Maximizing player (Bot 'O')
            best = -float('inf') # Initialize with negative infinity
            for r_iter in range(BOARD_SIZE):
                for c_iter in range(BOARD_SIZE):
                    temp_board = copy.deepcopy(board_state) # Create a new temporary board for simulation
                    temp_evolve_marks = copy.deepcopy(evolve_marks_state)

                    current_r, current_c = r_iter, c_iter
                    # Apply 'Gravity Tic-Tac-Toe' for minimax consideration
                    if st.session_state.selected_twists["Gravity Tic-Tac-Toe"]:
                        actual_r = self._get_gravity_placement(temp_board, c_iter)
                        if actual_r is None: # Column is full, skip this potential move
                            continue
                        current_r = actual_r

                    if temp_board[current_r][current_c] == EMPTY_CELL:
                        temp_board[current_r][current_c] = PLAYER_O # Make the move
                        if st.session_state.selected_twists["Evolve Tic-Tac-Toe"]:
                            temp_evolve_marks[(current_r, c_iter)] = temp_evolve_marks.get((current_r, c_iter), 0) + 1
                        
                        # Recursively call minimax for the next player (Minimizing)
                        best = max(best, self._minimax(temp_board, temp_evolve_marks, depth + 1, False))
            return best
        else: # Minimizing player (Human 'X')
            best = float('inf') # Initialize with positive infinity
            for r_iter in range(BOARD_SIZE):
                for c_iter in range(BOARD_SIZE):
                    temp_board = copy.deepcopy(board_state)
                    temp_evolve_marks = copy.deepcopy(evolve_marks_state)

                    current_r, current_c = r_iter, c_iter
                    if st.session_state.selected_twists["Gravity Tic-Tac-Toe"]:
                        actual_r = self._get_gravity_placement(temp_board, c_iter)
                        if actual_r is None:
                            continue
                        current_r = actual_r

                    if temp_board[current_r][current_c] == EMPTY_CELL:
                        temp_board[current_r][c_iter] = PLAYER_X # Make the move
                        if st.session_state.selected_twists["Evolve Tic-Tac-Toe"]:
                            temp_evolve_marks[(current_r, c_iter)] = temp_evolve_marks.get((current_r, c_iter), 0) + 1
                        
                        # Recursively call minimax for the next player (Maximizing)
                        best = min(best, self._minimax(temp_board, temp_evolve_marks, depth + 1, True))
            return best

# Main Streamlit application entry point
def app():
    # Create an instance of the game logic class.
    # This will also ensure st.session_state is initialized.
    game = TwistedTicTacToeStreamlit()

    # Route to the appropriate screen based on session state
    if st.session_state.current_screen == "twist_selection":
        game.display_twist_selection_screen()
    elif st.session_state.current_screen == "game_board":
        game.display_game_board_screen()

if __name__ == "__main__":
    app()

