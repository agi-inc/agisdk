# Browser Automation Actions

This document provides a minimal explanation of each action, its format, and examples.

## Basic Actions

### noop
Wait for a specified amount of time.
```python
noop(wait_ms=1000)  # Wait 1000ms
```

### fill
Fill an input element with text.
```python
fill('108', 'Example text')  # Fill element with bid '108'
```

### click
Click on an element.
```python
click('121')  # Basic click
click('121', button='right')  # Right click
click('121', modifiers=['Shift'])  # Shift+click
```

### hover
Hover over an element.
```python
hover('108')  # Hover over element with bid '108'
```

### focus
Focus on an element.
```python
focus('108')  # Focus element with bid '108'
```

### press
Press keyboard keys on a focused element.
```python
press('108', 'Enter')  # Press Enter on element
press('108', 'Control+a')  # Press Ctrl+A (select all)
```

### press_key
Press a single keyboard key. (Element agnostic)
```python
press_key('Escape')  # Press Escape key
press_key('Tab')     # Press Tab key
press_key('Enter')   # Press Enter key
press_key('F5')      # Press F5 key
```

### clear
Clear the content of an input element.
```python
clear('108')  # Clear element with bid '108'
```

## Form Actions

### select_option
Select option(s) in a select element.
```python
select_option('108', 'Option 1')  # Select single option
select_option('108', ['Option 1', 'Option 2'])  # Select multiple options
```

### upload_file
Upload file(s) to an input element.
```python
upload_file('108', 'path/to/file.pdf')  # Upload single file
upload_file('108', ['file1.jpg', 'file2.jpg'])  # Upload multiple files
```

## Mouse Actions

### dblclick
Double-click on an element.
```python
dblclick('108')  # Double-click element with bid '108'
```

### drag_and_drop
Drag one element and drop onto another.
```python
drag_and_drop('108', '109')  # Drag from '108' to '109'
```

### scroll
Scroll the page by specified amounts.
```python
scroll(0, 200)  # Scroll down 200px
scroll(-100, 0)  # Scroll left 100px
```

## Navigation Actions

### goto
Navigate to a URL.
```python
goto('https://example.com')  # Navigate to URL
```

### go_back
Navigate back in browser history.
```python
go_back()  # Go back one page
```

### go_forward
Navigate forward in browser history.
```python
go_forward()  # Go forward one page
```

## Tab Management

### new_tab
Open a new browser tab.
```python
new_tab('https://example.com')  # Open URL in new tab
new_tab()  # Open empty new tab
```

### tab_close
Close the current tab.
```python
tab_close()  # Close current tab
```

### tab_focus
Focus on a specific tab by index.
```python
tab_focus(1)  # Focus on second tab (0-indexed)
```

## Communication Actions

### send_msg_to_user
Send a message to the user.
```python
send_msg_to_user('I found the information you requested.')
```

## Common Patterns

### Selecting from dropdowns
```python
click('108')  # Open dropdown
click('136')  # Select option
```

```python
fill('108', 'Option text')  # For autocomplete fields
click('136') # Then select an option
```

### Navigation through pages
```python
goto('https://example.com')
click('108')  # Click a navigation link
noop(1000)  # Wait for new page to load
```