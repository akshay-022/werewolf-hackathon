**Detailed README for Werewolf Assistant**

This README provides a comprehensive guide to using the Werewolf Assistant program, a tool designed to aid in your strategic thinking and information tracking during a game of Werewolf.

**Getting Started**

1. **Import the `MemoryStorer` class:**
   ```python
   from werewolf_assistant import MemoryStorer
   ```
2. **Initialize the `MemoryStorer` object:** Create an instance of the `MemoryStorer` class, providing your name as an argument:
   ```python
   my_name = "Your Name"
   memory_storer = MemoryStorer(my_name)
   ```

**Key Functions for Tracking Game Information**

* **`initialize_player(player_name)`:** Adds a new player to the tracking list.
* **`add_claim(player_name, content, channel)`:** Records a claim made by a player, including the content, channel, and timestamp.
* **`record_vote(voter, target)`:** Records a vote cast during the day phase.
* **`mark_player_dead(player_name)`:** Marks a player as deceased.
* **`update_suspicion_score(player_name, delta)`:** Adjusts a player's suspicion score.
* **`set_suspected_role(player_name, role)`:** Sets your suspected role for a player.
* **`get_alive_players()`:** Returns a list of players who are still alive.
* **`get_most_suspicious_players(count=3)`:** Returns a list of the most suspicious players.
* **`get_player_claims(player_name)`:** Returns all claims made by a specific player.
* **`get_all_data()`:** Returns a dictionary containing all stored data for analysis.

**Functions for Tracking Your Own Information and Strategy**

* **`update_my_role(role)`:** Updates your actual role in the game (e.g., villager, werewolf, seer, etc.).
* **`update_my_claimed_role(role)`:** Updates the role you've publicly claimed to be.
* **`add_my_claim(content, channel)`:** Records a claim you've made.
* **`update_alliance(player_name, trust_level, reason=None)`:** Updates your trust level with another player.
* **`mark_enemy(player_name, reason)`:** Marks a player as an enemy.
* **`add_thought_process(reasoning, context=None)`:** Records your reasoning process.
* **`record_key_event(event_type, details, players_involved)`:** Records significant game events.
* **`add_behavioral_note(player_name, observation)`:** Records observations about a player's behavior.
* **`record_vote_justification(target, reason)`:** Records your justification for voting for a player.
* **`update_strategy(new_strategy, reason)`:** Updates your current strategic approach.
* **`record_role_action(target, action_type, result=None)`:** Records specific actions taken by your role (e.g., investigating, protecting, revealing pack members).
* **`get_my_state()`:** Returns a dictionary containing your current state, including claims, alliances, enemies, strategy, and more.

**Additional Tips**

* **Regularly update the `MemoryStorer`:** Keep the information up-to-date throughout the game.
* **Utilize the `get_most_suspicious_players()` function:** Prioritize your attention on the most suspicious players.
* **Review claims and voting history:** Analyze the consistency and credibility of players' claims.
* **Consider player behavior and patterns:** Look for inconsistencies or suspicious behavior.
* **Adapt your strategy:** Be flexible and adjust your strategy based on new information and changing circumstances.

By effectively using the Werewolf Assistant, you can gain a significant advantage in your game. Remember to adapt the code and functions to fit your specific game needs and preferences.
