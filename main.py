#!/usr/bin/env python3
"""
Yahoo Fantasy Sports Tool
A minimal read-only app to compare your team's current week performance
across all 9 categories against other teams in your league.
"""

import os
import sys
from yahoofantasy import Context
from yahoofantasy import League, Team

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'  # Bright green
    YELLOW = '\033[93m'  # Bright yellow
    RED = '\033[91m'    # Bright red
    RESET = '\033[0m'   # Reset to default


def authenticate():
    """Authenticate with Yahoo Fantasy Sports API."""
    print("Authenticating with Yahoo Fantasy Sports API...")
    
    try:
        # Try to use existing authentication from 'yahoofantasy login'
        ctx = Context()
        print("✓ Using existing authentication")
        return ctx
    except ValueError as e:
        # If no existing auth, check for environment variables
        client_id = os.getenv('YAHOO_CLIENT_ID')
        client_secret = os.getenv('YAHOO_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            print("Error: No existing authentication found.")
            print("\nYou need to either:")
            print("  1. Run 'yahoofantasy login' first (recommended), OR")
            print("  2. Set YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET environment variables")
            sys.exit(1)
        
        print("Using credentials from environment variables...")
        print("You will be prompted to authorize this application in your browser.")
        
        ctx = Context(client_id=client_id, client_secret=client_secret)
        
        # This will open a browser for OAuth authorization
        # The token will be cached for future use
        try:
            ctx.authenticate()
            print("✓ Authentication successful!")
            return ctx
        except Exception as e:
            print(f"Error during authentication: {e}")
            sys.exit(1)

def select_sport():
    """Allow user to select a sport."""
    sports = {
        '1': ('nba', 'NBA'),
        '2': ('nfl', 'NFL'),
        '3': ('nhl', 'NHL'),
        '4': ('mlb', 'MLB'),
    }
    
    print("\nSelect a sport:")
    for key, (code, name) in sports.items():
        print(f"  {key}. {name}")
    
    while True:
        choice = input("\nSelect sport (1-4, default: 1 for NBA): ").strip() or '1'
        if choice in sports:
            return sports[choice][0]
        print("Please enter 1, 2, 3, or 4")


def select_league(ctx: Context, sport='nba'):
    """Allow user to select a league from their available leagues."""
    print("\nFetching your leagues...")
    
    try:
        # Get current year
        current_year = 2025
        print(f"Defaulting to {current_year}")
        
        # Try to get leagues for current year, fallback to previous year if needed
        leagues = []
        try:
            leagues = ctx.get_leagues(sport, current_year)
        except:
            # throw error
            raise Exception("No leagues found for " + sport + " in " + current_year)
        
        if not leagues:
            print(f"No leagues found for {sport}.")
            sys.exit(1)
        
        print(f"\nFound {len(leagues)} league(s):")
        for i, league in enumerate(leagues, 1):
            print(f"  {i}. {league.name} (ID: {league.league_id})")
        
        while True:
            try:
                choice = input(f"\nSelect a league (1-{len(leagues)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(leagues):
                    selected_league = leagues[idx]
                    print(f"\n✓ Selected: {selected_league.name}")
                    return selected_league
                else:
                    print(f"Please enter a number between 1 and {len(leagues)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\n\nExiting...")
                sys.exit(0)
    
    except Exception as e:
        print(f"Error fetching leagues: {e}")
        sys.exit(1)


def sync_league_data(league: League, week: int):
    """
    Sync league data from scoreboard to ensure game_code and other attributes are set.
    This is necessary for the library to properly access matchup stats.
    """
    try:
        from yahoofantasy.api.parse import from_response_object
        
        # Fetch scoreboard data which includes league info
        week_data = league.ctx._load_or_fetch(
            f"weeks.{league.id}.{week}",
            f"scoreboard;week={week}",
            league=league.id,
        )
        
        # Extract and sync league info from scoreboard response
        league_info = week_data["fantasy_content"]["league"]
        from_response_object(league, league_info)
        
        return True
    except Exception as e:
        print(f"Warning: Could not sync league data: {e}")
        return False


def get_current_week(league: League):
    """Get the current week number for the league."""
    try:
        # Try to get current week from league settings
        if hasattr(league, 'current_week'):
            return league.current_week
        # Try method call
        current_week = league.current_week()
        return current_week
    except:
        # Fallback: try to determine from scoreboard
        try:
            # Fetch scoreboard for week 1 to get league info
            week_data = league.ctx._load_or_fetch(
                f"weeks.{league.id}.1",
                f"scoreboard;week=1",
                league=league.id,
            )
            league_info = week_data["fantasy_content"]["league"]
            if "current_week" in league_info:
                from yahoofantasy.api.parse import get_value
                return get_value(league_info["current_week"])
        except:
            pass
    
    # Default fallback
    return 1


def select_team(league: League):
    """Allow user to select a team from the league."""
    print("\nFetching teams in the league...")
    
    try:
        teams = league.teams()
        
        if not teams:
            print("No teams found in this league.")
            sys.exit(1)
        
        print(f"\nFound {len(teams)} team(s):")
        for i, team in enumerate(teams, 1):
            print(f"  {i}. {team.name} (Manager: {team.manager.nickname if hasattr(team, 'manager') else 'N/A'})")
        
        while True:
            try:
                choice = input(f"\nSelect your team (1-{len(teams)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(teams):
                    selected_team = teams[idx]
                    print(f"\n✓ Selected: {selected_team.name}")
                    return selected_team
                else:
                    print(f"Please enter a number between 1 and {len(teams)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\n\nExiting...")
                sys.exit(0)
    
    except Exception as e:
        print(f"Error fetching teams: {e}")
        sys.exit(1)


def get_all_team_stats_from_matchups(league: League, week: int):
    """
    Get stats for all teams from matchups for a specific week.
    Returns a dictionary mapping team_id to a list of Stat objects.
    """
    team_stats_dict = {}
    
    try:
        # Use Week object to get matchups (this is the proper way)
        from yahoofantasy.resources.week import Week
        week_obj = Week(league.ctx, league, week)
        week_obj.sync()
        
        for matchup in week_obj.matchups:
            try:
                # Get stats from team1
                if hasattr(matchup, 'team1_stats'):
                    team1_stats = matchup.team1_stats
                    if team1_stats:
                        team1 = matchup.team1
                        if team1 and hasattr(team1, 'team_id'):
                            team_stats_dict[team1.team_id] = team1_stats
            except Exception as e:
                print(f"Warning: Could not get team1_stats: {e}")
            
            try:
                # Get stats from team2
                if hasattr(matchup, 'team2_stats'):
                    team2_stats = matchup.team2_stats
                    if team2_stats:
                        team2 = matchup.team2
                        if team2 and hasattr(team2, 'team_id'):
                            team_stats_dict[team2.team_id] = team2_stats
            except Exception as e:
                print(f"Warning: Could not get team2_stats: {e}")
        
        return team_stats_dict
    except Exception as e:
        print(f"Warning: Could not fetch stats from matchups for week {week}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def get_category_info_from_stats(stats_list):
    """
    Extract category information from a list of Stat objects.
    Returns a list of dictionaries with category info.
    """
    categories_info = []
    
    if not stats_list:
        return categories_info
    
    # Stat objects have .display attribute for the category name
    # Use .id for stat_id (the library uses .id not .stat_id)
    for idx, stat in enumerate(stats_list):
        if hasattr(stat, 'display') and stat.display:
            category_name = stat.display
            # Skip ratio stats (FGM/FGA, FTM/FTA) as they're not useful for comparison
            if "/" in category_name and category_name not in ["A/T"]:
                continue
            
            # Get stat_id from .id attribute
            stat_id = None
            if hasattr(stat, 'id'):
                stat_id = str(stat.id)
            else:
                # Use index as fallback
                stat_id = str(idx)
            
            categories_info.append({
                'id': stat_id,
                'name': category_name,
                'index': idx
            })
    
    return categories_info


def is_percentage_stat(stat_id_or_index, stat_display=None):
    """
    Check if a stat is a percentage stat based on stat ID or display name.
    Percentage stats in NBA: FG% (5), FT% (8), 3PT% (11)
    """
    percentage_stat_ids = {'5', '8', '11'}  # FG%, FT%, 3PT%
    
    if isinstance(stat_id_or_index, str) and stat_id_or_index in percentage_stat_ids:
        return True
    
    if stat_display and '%' in stat_display:
        return True
    
    return False


def convert_percentage_value(raw_value):
    """
    Convert Yahoo's percentage format to a percentage decimal.
    
    The yahoofantasy library may already convert percentages to decimals.
    If the value is already < 1, it's likely already a decimal (0.454 = 45.4%).
    If the value is >= 1, it needs conversion:
    - 454 = 45.4% (divide by 10 to get 45.4, then divide by 100 to get 0.454)
    - 4540 = 45.4% (divide by 100 to get 45.4, then divide by 100 to get 0.454)
    
    Returns the percentage as a decimal (0.454 for 45.4%)
    """
    try:
        val = float(raw_value)
        
        # If value is already < 1, it's likely already converted to decimal format
        # The yahoofantasy library may have already done the conversion
        if val < 1.0:
            return val
        
        # If value is >= 1000, likely format is 4540 = 45.4%
        # Divide by 100 to get 45.4, then by 100 to get 0.454
        if val >= 1000:
            return (val / 100.0) / 100.0
        
        # If value is >= 100, likely format is 454 = 45.4%
        # Divide by 10 to get 45.4, then by 100 to get 0.454
        elif val >= 100:
            return (val / 10.0) / 100.0
        
        # If value is between 1 and 100, likely format is 45.4 = 45.4%
        # But this is ambiguous - could be 45.4% or 0.454%
        # Assume it's already a percentage value, divide by 100
        elif val >= 1:
            return val / 100.0
        
        # Shouldn't reach here if val < 1, but just in case
        return val
    except (ValueError, TypeError):
        return None


def extract_stat_value(stats_list, stat_id_or_index, stat_display=None):
    """
    Extract a stat value from a list of Stat objects.
    stats_list: List of Stat objects from matchup.team1_stats or matchup.team2_stats
    stat_id_or_index: Either a stat_id (string) or index (int) to find the stat
    stat_display: Optional display name of the stat (for percentage detection)
    """
    if not stats_list:
        return None
    
    try:
        # Handle empty values (APIAttr objects that are empty dicts)
        from yahoofantasy.api.attr import APIAttr
        
        # Determine if this is a percentage stat
        is_percentage = is_percentage_stat(stat_id_or_index, stat_display)
        
        # Always try to find by stat.id first (most reliable)
        # Only use index as a last resort fallback
        for stat in stats_list:
            if hasattr(stat, 'id') and str(stat.id) == str(stat_id_or_index):
                if hasattr(stat, 'value'):
                    val = stat.value
                    if isinstance(val, APIAttr) and not val.__dict__:
                        return None
                    if val == "/" or val == "":
                        return None
                    
                    # Convert percentage values
                    if is_percentage:
                        converted = convert_percentage_value(val)
                        return converted if converted is not None else None
                    
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return val if val else None
        
        # Fallback: use index if stat_id_or_index is numeric
        try:
            idx = int(stat_id_or_index)
            if 0 <= idx < len(stats_list):
                stat = stats_list[idx]
                if hasattr(stat, 'value'):
                    val = stat.value
                    if isinstance(val, APIAttr) and not val.__dict__:
                        return None
                    if val == "/" or val == "":
                        return None
                    
                    # Check if this stat is a percentage by display name
                    if hasattr(stat, 'display') and '%' in stat.display:
                        converted = convert_percentage_value(val)
                        return converted if converted is not None else None
                    
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return val if val else None
        except (ValueError, TypeError):
            pass
        
    except Exception as e:
        pass
    
    return None


def is_lower_better_stat(category_name, stat_id=None):
    """
    Determine if lower values are better for a stat.
    Returns True if lower is better (e.g., turnovers), False if higher is better.
    """
    category_lower = category_name.lower()
    
    # Check for turnover-related names
    # Common names: "TO", "Turnovers", "Turnover", "TOV", etc.
    if "turnover" in category_lower:
        return True
    if category_lower in ["to", "tov"]:
        return True
    if category_lower.startswith("to ") or category_lower.endswith(" to"):
        return True
    
    # Check stat ID for turnovers (NBA turnover stat ID is typically 19)
    if stat_id and str(stat_id) == "19":
        return True
    
    return False


def get_color_for_performance(better_than, total_teams):
    """
    Get color code based on performance ratio.
    Returns color code string based on how many teams you're beating.
    """
    if total_teams == 0:
        return Colors.RESET
    
    ratio = better_than / total_teams
    
    # Green for top performance (beating 70%+ of teams)
    if ratio >= 0.7:
        return Colors.GREEN
    # Red for poor performance (beating < 30% of teams)
    elif ratio < 0.3:
        return Colors.RED
    # Yellow for middle performance (30-70%)
    else:
        return Colors.YELLOW


def compare_teams(selected_team: Team, all_teams: list, league: League, week: int):
    """Compare selected team's stats against all other teams."""
    print(f"\n{'='*80}")
    print(f"Comparing {selected_team.name} (Week {week})")
    print(f"{'='*80}\n")
    
    # Get stats for all teams from matchups
    print("Fetching stats for all teams from matchups...")
    all_team_stats = get_all_team_stats_from_matchups(league, week)
    
    if not all_team_stats:
        print("Could not retrieve stats for any teams.")
        return
    
    # Get category information from the first team's stats (all teams have same categories)
    # Find a team with stats to get category names
    sample_stats = None
    for team_id, stats_list in all_team_stats.items():
        if stats_list:
            sample_stats = stats_list
            break
    if not sample_stats:
        print("Could not determine league categories.")
        return
    
    categories_info = get_category_info_from_stats(sample_stats)
    
    if not categories_info:
        print("Could not determine league categories.")
        return
    
    # Get selected team's stats
    selected_team_id = selected_team.team_id
    selected_stats = all_team_stats.get(selected_team_id)
    
    if not selected_stats:
        print(f"Could not retrieve stats for {selected_team.name} in week {week}.")
        print("Note: Your team may not have a matchup this week, or stats are not yet available.")
        return
    
    # Build team lookup dictionary
    team_lookup = {team.team_id: team for team in all_teams}
    
    # For each category, compare selected team against all others
    print(f"\n{'Category':<40} {'Your Team':<15} {'vs Teams':<20} {'Best':<20} {'Worst':<20}")
    print("-" * 115)
    
    for cat_info in categories_info:
        stat_id = cat_info.get('id')  # Use stat ID, not index
        category_name = cat_info['name']
        
        if not stat_id:
            # Fallback to index only if ID is not available
            stat_id = str(cat_info.get('index'))
        
        # Get selected team's value for this category
        selected_value = extract_stat_value(selected_stats, stat_id, category_name)
        
        if selected_value is None:
            print(f"{category_name:<40} {'N/A':<15} {'-':<20} {'-':<20} {'-':<20}")
            continue
        
        # Get all teams' values (including selected team) for best/worst calculation
        # Also get other teams' values (excluding selected) for "vs Teams" calculation
        all_values = []
        other_values = []
        
        for team_id, stats_list in all_team_stats.items():
            if team_id not in team_lookup:
                continue
            
            value = extract_stat_value(stats_list, stat_id, category_name)
            if value is not None:
                team_name = team_lookup[team_id].name
                all_values.append((team_name, value))
                
                # Add to other_values only if not the selected team
                if team_id != selected_team_id:
                    other_values.append((team_name, value))
        
        if not all_values:
            # No values available for any team
            print(f"{category_name:<40} {'N/A':<15} {'-':<20} {'-':<20} {'-':<20}")
            continue
        
        # Determine if higher is better (most stats) or lower is better (turnovers, etc.)
        # Turnovers: lower is better
        # Everything else (including percentages): higher is better
        higher_is_better = not is_lower_better_stat(category_name, stat_id)
        
        # Sort all values (including selected team) to find best/worst
        sorted_all_values = sorted(all_values, key=lambda x: x[1], reverse=higher_is_better)
        best_team, best_value = sorted_all_values[0]
        worst_team, worst_value = sorted_all_values[-1]
        
        # Count how many OTHER teams you're better than (for "vs Teams" column)
        if not other_values:
            # No other teams to compare against
            vs_teams = "0/0"
            vs_teams_colored = "-"
        else:
            if higher_is_better:
                better_than = sum(1 for _, val in other_values if selected_value > val)
            else:
                better_than = sum(1 for _, val in other_values if selected_value < val)
            
            vs_teams = f"{better_than}/{len(other_values)}"
            # Get color for performance
            color = get_color_for_performance(better_than, len(other_values))
            vs_teams_colored = f"{color}{vs_teams}{Colors.RESET}"
        
        # Format the value display
        # For percentages, values are already converted to decimals (0.850 = 85.0%)
        # Display as percentage with 1 decimal place
        if isinstance(selected_value, float):
            if "%" in category_name:
                # Convert decimal to percentage: 0.850 -> 85.0%
                selected_str = f"{selected_value * 100:.1f}%"
            else:
                selected_str = f"{selected_value:.2f}"
        else:
            selected_str = str(selected_value)
        
        if isinstance(best_value, float):
            if "%" in category_name:
                best_str = f"{best_value * 100:.1f}% ({best_team[:15]})"
            else:
                best_str = f"{best_value:.2f} ({best_team[:15]})"
        else:
            best_str = f"{best_value} ({best_team[:15]})"
        
        if isinstance(worst_value, float):
            if "%" in category_name:
                worst_str = f"{worst_value * 100:.1f}% ({worst_team[:15]})"
            else:
                worst_str = f"{worst_value:.2f} ({worst_team[:15]})"
        else:
            worst_str = f"{worst_value} ({worst_team[:15]})"
        
        print(f"{category_name:<40} {selected_str:<15} {vs_teams_colored:<20} {best_str:<20} {worst_str:<20}")
    
    print("\n" + "="*115)
    print("Note: 'vs Teams' shows how many teams you're better than out of total teams")
    print("      Percentages are shown with 1 decimal place, other stats with 2")
    print(f"      {Colors.GREEN}Green{Colors.RESET} = beating 70%+ teams, {Colors.YELLOW}Yellow{Colors.RESET} = 30-70%, {Colors.RED}Red{Colors.RESET} = <30%")
    print("="*115)
    
    # Show head-to-head matchups
    compare_head_to_head(selected_team, selected_stats, all_teams, all_team_stats, categories_info)


def compare_head_to_head(selected_team: Team, selected_stats: list, all_teams: list,
                         all_team_stats: dict, categories_info: list):
    """
    Compare selected team head-to-head against each other team.
    Shows the category win-loss record for each matchup.
    """
    print(f"\n{'='*115}")
    print(f"Head-to-Head Matchups: {selected_team.name}")
    print(f"{'='*115}\n")
    
    # Build team lookup dictionary
    team_lookup = {team.team_id: team for team in all_teams}
    selected_team_id = selected_team.team_id
    
    # Header
    print(f"{'Opponent':<30} {'Score':<12} {'Wins':<8} {'Losses':<8} {'Categories (W=Win, L=Loss, T=Tie)'}")
    print("-" * 115)
    
    matchup_results = []
    
    for team_id, stats_list in all_team_stats.items():
        if team_id == selected_team_id:
            continue
        
        if team_id not in team_lookup:
            continue
        
        opponent_team = team_lookup[team_id]
        opponent_stats = stats_list
        
        # Compare category by category
        wins = 0
        losses = 0
        category_results = []
        
        for cat_info in categories_info:
            stat_id = cat_info.get('id')
            category_name = cat_info['name']
            
            if not stat_id:
                continue
            
            # Get values for both teams
            selected_value = extract_stat_value(selected_stats, stat_id, category_name)
            opponent_value = extract_stat_value(opponent_stats, stat_id, category_name)
            
            if selected_value is None or opponent_value is None:
                continue
            
            # Determine if higher is better
            higher_is_better = not is_lower_better_stat(category_name, stat_id)
            
            # Compare values
            if higher_is_better:
                if selected_value > opponent_value:
                    wins += 1
                    category_results.append((category_name, 'W'))
                elif selected_value < opponent_value:
                    losses += 1
                    category_results.append((category_name, 'L'))
                else:
                    category_results.append((category_name, 'T'))
            else:
                # Lower is better (turnovers)
                if selected_value < opponent_value:
                    wins += 1
                    category_results.append((category_name, 'W'))
                elif selected_value > opponent_value:
                    losses += 1
                    category_results.append((category_name, 'L'))
                else:
                    category_results.append((category_name, 'T'))
        
        # Create score string
        score = f"{wins}-{losses}"
        
        matchup_results.append({
            'team': opponent_team,
            'score': score,
            'wins': wins,
            'losses': losses,
            'category_results': category_results  # Store full results for display
        })
    
    # Sort by wins (descending) to show best matchups first
    matchup_results.sort(key=lambda x: x['wins'], reverse=True)
    
    # Display results
    for result in matchup_results:
        team_name = result['team'].name
        score = result['score']
        wins = result['wins']
        losses = result['losses']
        category_results = result['category_results']
        
        # Color code the score based on win/loss
        # Green for winning matchups (wins > losses)
        # Yellow for losing or tie matchups (wins <= losses)
        if wins > losses:
            score_color = Colors.GREEN
        else:
            score_color = Colors.YELLOW
        score_colored = f"{score_color}{score}{Colors.RESET}"
        
        # Format category results with colors
        category_display = []
        for cat_name, result_code in category_results:
            if result_code == 'W':
                color = Colors.GREEN
            elif result_code == 'L':
                color = Colors.RED
            else:  # T for tie
                color = Colors.YELLOW
            # Abbreviate longer category names for compact display
            cat_display = cat_name
            if len(cat_name) > 8:
                if 'Percentage' in cat_name:
                    cat_display = cat_name.replace(' Percentage', '%')
                elif 'Made' in cat_name:
                    cat_display = cat_name.replace(' Made', 'M')
            
            category_display.append(f"{color}{cat_display}:{result_code}{Colors.RESET}")
        
        # Join categories with spacing
        categories_str = "  ".join(category_display)
        
        print(f"{team_name:<30} {score_colored:<20} {wins:<8} {losses:<8} {categories_str}")
    
    print("\n" + "="*115)
    print("Note: Score shows wins-losses for your team. Categories show W=Win (green), L=Loss (red), T=Tie (yellow)")
    print("="*115)


def main():
    """Main application entry point."""
    print("="*80)
    print("Yahoo Fantasy Sports Team Comparison Tool")
    print("="*80)
    
    # Authenticate
    ctx = authenticate()
    
    # Select sport
    sport = select_sport()
    
    # Select league
    league = select_league(ctx, sport)
    
    # Get current week
    current_week = get_current_week(league)
    print(f"\nCurrent week: {current_week}")
    
    # Sync league data to ensure game_code and other attributes are set
    # This is critical for accessing matchup stats in category leagues
    print("\nSyncing league data...")
    if sync_league_data(league, current_week):
        print("✓ League data synced successfully")
    else:
        print("⚠ Warning: League data sync had issues, but continuing...")
    
    # Get matchups for current week
    print(f"\nFetching matchups for week {current_week}...")
    try:
        from yahoofantasy.resources.week import Week
        week_obj = Week(ctx, league, current_week)
        week_obj.sync()
        matchups = week_obj.matchups
        
        print(f"Found {len(matchups)} matchup(s) for week {current_week}")
        for matchup in matchups:
            team1_name = matchup.team1.name if hasattr(matchup, 'team1') and matchup.team1 else "TBD"
            team2_name = matchup.team2.name if hasattr(matchup, 'team2') and matchup.team2 else "TBD"
            print(f"  {team1_name} vs {team2_name}")
    except Exception as e:
        print(f"Warning: Could not fetch matchups: {e}")
        import traceback
        traceback.print_exc()
    
    # Select team
    selected_team = select_team(league)
    
    # Get all teams for comparison
    all_teams = league.teams()
    
    # Compare teams
    compare_teams(selected_team, all_teams, league, current_week)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

