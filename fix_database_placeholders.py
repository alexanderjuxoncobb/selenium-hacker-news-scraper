#!/usr/bin/env python3
"""
Quick fix for all database parameter placeholders
"""

import re

def fix_placeholders():
    with open('dashboard/database.py', 'r') as f:
        content = f.read()
    
    # Replace all ? with {placeholder} in SQL queries
    # This regex finds SQL queries that contain ? placeholders
    pattern = r'(cursor\.execute\("""[\s\S]*?""", \([^)]*\)\))'
    
    def replace_question_marks(match):
        sql_block = match.group(1)
        # Count number of ? in the SQL
        question_count = sql_block.count('?')
        if question_count > 0:
            # Replace with f-string template
            sql_block = sql_block.replace('cursor.execute("""', 'placeholder = self._get_placeholder()\n            cursor.execute(f"""')
            # Replace each ? with {placeholder}
            for i in range(question_count):
                sql_block = sql_block.replace('?', '{placeholder}', 1)
        return sql_block
    
    # Apply the replacement
    fixed_content = re.sub(pattern, replace_question_marks, content, flags=re.MULTILINE)
    
    with open('dashboard/database.py', 'w') as f:
        f.write(fixed_content)
    
    print("✅ Fixed all database parameter placeholders")

if __name__ == "__main__":
    fix_placeholders()