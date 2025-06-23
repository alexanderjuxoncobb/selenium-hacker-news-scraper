#!/usr/bin/env python3
"""
Fix all remaining SQL parameter placeholders
"""

import re

# List of methods that need fixing (based on grep results)
fixes_needed = [
    # Method at line 757: check_story_interaction
    (757, "WHERE user_id = ? AND story_id = ?", 2),
    
    # Method at line 1108: get_user_relevant_stories_by_date  
    (1108, "WHERE s.date = ? AND usr.user_id = ? AND usr.is_relevant = 1", 3),
    
    # Method at lines 1195, 1201: log_interaction
    (1195, "WHERE user_id = ? AND story_id = ? AND interaction_type = ?", 3),
    (1201, "WHERE user_id = ? AND story_id = ? AND interaction_type = ?", 3),
    
    # Method at line 1238: check_interaction
    (1238, "WHERE user_id = ? AND story_id = ? AND interaction_type = ?", 3),
    
    # Method at line 1255: get_saved_stories
    (1255, "WHERE ui.user_id = ? AND ui.interaction_type = 'save'", 1),
    
    # Method at line 1309: save_story_notes (complex case)
    (1309, "COALESCE((SELECT created_at FROM story_notes WHERE user_id = ? AND story_id = ?), ?)", 3),
    
    # Method at line 1330: get_story_notes
    (1330, "SELECT notes FROM story_notes WHERE user_id = ? AND story_id = ?", 2),
    
    # Method at line 1352: get_user_interaction_stats (with datetime function)
    (1352, "WHERE user_id = ? AND timestamp > datetime('now', '-{} days')", 1),
    
    # Method at line 1733: get_all_stories_with_relevance
    (1733, "LEFT JOIN user_story_relevance r ON s.id = r.story_id AND r.user_id = ?", 1),
    
    # Method at line 1772: _get_current_interests_with_categories
    (1772, "WHERE user_id = ?", 1),
]

def fix_placeholders():
    with open('dashboard/database.py', 'r') as f:
        lines = f.readlines()
    
    # Track which lines to modify
    modifications = {}
    
    for line_num, pattern, placeholder_count in fixes_needed:
        # Adjust for 0-based indexing
        idx = line_num - 1
        
        if idx < len(lines) and pattern in lines[idx]:
            # Replace ? with {placeholder}
            new_line = lines[idx]
            for i in range(placeholder_count):
                new_line = new_line.replace('?', '{placeholder}', 1)
            
            # Check if we need to add f-string prefix
            if 'cursor.execute("""' in new_line:
                new_line = new_line.replace('cursor.execute("""', 'cursor.execute(f"""')
            elif 'cursor.execute("' in new_line:
                new_line = new_line.replace('cursor.execute("', 'cursor.execute(f"')
            
            modifications[idx] = new_line
            
            # Also need to add placeholder variable before the execute
            # Find the line with cursor.execute
            for i in range(max(0, idx - 10), idx):
                if 'cursor = conn.cursor()' in lines[i]:
                    # Add placeholder line after cursor creation
                    if i + 1 not in modifications:
                        modifications[i + 1] = lines[i + 1].rstrip() + '\n' + ' ' * 12 + 'placeholder = self._get_placeholder()\n'
                    break
    
    # Apply modifications
    for idx, new_content in sorted(modifications.items()):
        if idx < len(lines):
            lines[idx] = new_content
    
    # Write back
    with open('dashboard/database.py', 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Fixed {len(fixes_needed)} SQL statements")

if __name__ == "__main__":
    fix_placeholders()