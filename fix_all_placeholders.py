#!/usr/bin/env python3
"""
Fix ALL remaining SQL parameter placeholders in database.py
"""

import re

def fix_all_placeholders():
    with open('dashboard/database.py', 'r') as f:
        content = f.read()
    
    # Find all cursor.execute calls that use ? placeholders
    # This regex finds cursor.execute calls with SQL containing ?
    pattern = r'(cursor\.execute\((?:f?"""[\s\S]*?\?[\s\S]*?"""|\s*"[^"]*\?"[^"]*),\s*\([^)]*\)\))'
    
    fixes_made = []
    
    # Function to replace ? with proper placeholder
    def fix_execute(match):
        execute_call = match.group(1)
        
        # Skip if already using placeholder variable
        if 'placeholder' in execute_call or '{placeholder}' in execute_call:
            return execute_call
        
        # Skip if it's already in a db_type check block
        if execute_call.count('sqlite') > 0 or execute_call.count('postgresql') > 0:
            return execute_call
            
        # Count number of ? in the SQL
        question_marks = execute_call.count('?')
        if question_marks == 0:
            return execute_call
            
        # Extract the SQL and parameters
        sql_match = re.search(r'cursor\.execute\((f?"""[\s\S]*?"""|"[^"]*")', execute_call)
        if not sql_match:
            return execute_call
            
        sql_part = sql_match.group(1)
        
        # Log the fix
        fixes_made.append(f"Fixed {question_marks} placeholders in: {sql_part[:50]}...")
        
        # Build the replacement
        if sql_part.startswith('f"""') or sql_part.startswith('f"'):
            # It's already an f-string, just replace ? with {placeholder}
            new_sql = sql_part.replace('?', '{placeholder}')
            replacement = execute_call.replace(sql_part, new_sql)
            # Add placeholder variable before execute
            replacement = f'placeholder = self._get_placeholder()\n            {replacement}'
        else:
            # Convert to f-string
            new_sql = sql_part.replace('"""', 'f"""').replace('"', 'f"', 1)
            new_sql = new_sql.replace('?', '{placeholder}')
            replacement = execute_call.replace(sql_part, new_sql)
            # Add placeholder variable before execute
            replacement = f'placeholder = self._get_placeholder()\n            {replacement}'
        
        return replacement
    
    # Apply fixes
    fixed_content = re.sub(pattern, fix_execute, content, flags=re.MULTILINE)
    
    # Write back
    with open('dashboard/database.py', 'w') as f:
        f.write(fixed_content)
    
    print(f"✅ Fixed {len(fixes_made)} SQL statements with parameter placeholders")
    for fix in fixes_made:
        print(f"   - {fix}")

if __name__ == "__main__":
    fix_all_placeholders()