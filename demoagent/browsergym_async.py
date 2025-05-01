import json
import asyncio
import argparse
from typing import Dict, Any, List, Optional, Literal, Union
from playwright.async_api import async_playwright, Page

# Constants from browsergym
BROWSERGYM_ID_ATTRIBUTE = "browsergym_id"
BROWSERGYM_VISIBILITY_ATTRIBUTE = "browsergym_visibility_ratio"
BROWSERGYM_SETOFMARKS_ATTRIBUTE = "browsergym_set_of_marks"


async def extract_axtree(page: Page) -> Dict[str, Any]:
    """
    Extract the accessibility tree from a page using Chrome DevTools Protocol.
    
    Args:
        page: The Playwright page to extract the AXTree from
        
    Returns:
        A merged AXTree with the browsergym_id attributes populated
    """
    # Get the CDP client
    cdp = await page.context.new_cdp_session(page)
    
    # Mark elements with browsergym IDs
    js_frame_mark_elements = """
    /**
     * Go through all DOM elements in the frame (including shadowDOMs), give them unique browsergym
     * identifiers (bid), and store custom data in ARIA attributes.
     */
    async ([parent_bid, bid_attr_name, tags_to_mark]) => {

        // standard html tags
        // https://www.w3schools.com/tags/
        const html_tags = new Set([
            "a", "abbr", "acronym", "address", "applet", "area", "article", "aside", "audio",
            "b", "base", "basefont", "bdi", "bdo", "big", "blockquote", "body", "br", "button",
            "canvas", "caption", "center", "cite", "code", "col", "colgroup", "data", "datalist",
            "dd", "del", "details", "dfn", "dialog", "dir", "div", "dl", "dt", "em", "embed",
            "fieldset", "figcaption", "figure", "font", "footer", "form", "frame", "frameset",
            "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hgroup", "hr", "html", "i",
            "iframe", "img", "input", "ins", "kbd", "label", "legend", "li", "link", "main",
            "map", "mark", "menu", "meta", "meter", "nav", "noframes", "noscript", "object",
            "ol", "optgroup", "option", "output", "p", "param", "picture", "pre", "progress",
            "q", "rp", "rt", "ruby", "s", "samp", "script", "search", "section", "select",
            "small", "source", "span", "strike", "strong", "style", "sub", "summary", "sup",
            "svg", "table", "tbody", "td", "template", "textarea", "tfoot", "th", "thead",
            "time", "title", "tr", "track", "tt", "u", "ul", "var", "video", "wbr"
        ]);
        const set_of_marks_tags = new Set([
            "input", "textarea", "select", "button", "a", "iframe", "video", "li", "td", "option"
        ]);

        let browsergym_first_visit = false;
        // if no yet set, set the frame (local) element counter to 0
        if (!("browsergym_elem_counter" in window)) {
            window.browsergym_elem_counter = 0;
            window.browsergym_frame_id_generator = new IFrameIdGenerator();
            browsergym_first_visit = true;
        }
        // mechanism for computing all element's visibility
        // the intersection observer will set the visibility ratio of elements entering / exiting the viewport
        // a set is used to keep track of not-yet-visited elements
        let elems_to_be_visited = new Set();
        let intersection_observer = new IntersectionObserver(
            entries => {
              entries.forEach(entry => {
                let elem = entry.target;
                elem.setAttribute('browsergym_visibility_ratio', Math.round(entry.intersectionRatio * 100) / 100);
                if (elems_to_be_visited.has(elem)) {
                    elems_to_be_visited.delete(elem);
                }
              })
            },
            {
                threshold: [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            }
        )

        let all_bids = new Set();

        // get all DOM elements in the current frame (does not include elements in shadowDOMs)
        let elements = Array.from(document.querySelectorAll('*'));
        let som_buttons = [];
        i = 0;
        while (i < elements.length) {
            const elem = elements[i];
            // add shadowDOM elements to the elements array, in such a way that order is preserved
            if (elem.shadowRoot !== null) {
                elements = new Array(
                    ...Array.prototype.slice.call(elements, 0, i + 1),
                    ...Array.from(elem.shadowRoot.querySelectorAll("*")),
                    ...Array.prototype.slice.call(elements, i + 1)
                );
            }
            i++;
            // decide if the current element should be marked or not
            switch (tags_to_mark) {
                // mark all elements
                case "all":
                    break;
                // mark only standard HTML tags
                case "standard_html":
                    if (!elem.tagName || !html_tags.has(elem.tagName.toLowerCase())) {
                        // continue the loop, i.e., move on to the next element
                        continue;
                    }
                    break;
                // non-recognized argument
                default:
                    throw new Error(`Invalid value for parameter \\"tags_to_mark\\": ${JSON.stringify(tags_to_mark)}`);
            }
            // Processing element
            // register intersection callback on element, and keep track of element for waiting later
            elem.setAttribute('browsergym_visibility_ratio', 0);
            elems_to_be_visited.add(elem);
            intersection_observer.observe(elem);
            // write dynamic element values to the DOM
            if (typeof elem.value !== 'undefined') {
                elem.setAttribute("value", elem.value);
            }
            // write dynamic checked properties to the DOM
            if (typeof elem.checked !== 'undefined') {
                if (elem.checked === true) {
                    elem.setAttribute("checked", "");
                }
                else {
                    elem.removeAttribute("checked");
                }
            }
            // add the element global id (browsergym id) to a custom HTML attribute
            // https://playwright.dev/docs/locators#locate-by-test-id
            // recover the element id if it has one already, else compute a new element id
            let elem_global_bid = null;
            if (elem.hasAttribute(bid_attr_name)) {
                // throw an error if the attribute is already set while this is the first visit of the page
                if (browsergym_first_visit) {
                    throw new Error(`Attribute ${bid_attr_name} already used in element ${elem.outerHTML}`);
                }
                elem_global_bid = elem.getAttribute(bid_attr_name);
                // if the bid has already been encountered, then this is a duplicate and a new bid should be set
                if (all_bids.has(elem_global_bid)) {
                    console.log(`BrowserGym: duplicate bid ${elem_global_bid} detected, generating a new one`);
                    elem_global_bid = null;
                }
            }
            if (elem_global_bid === null) {
                let elem_local_id = null;
                // iFrames get alphabetical ids: 'a', 'b', ..., 'z', 'aA', 'aB' etc.
                if (['iframe', 'frame'].includes(elem.tagName.toLowerCase())) {
                    elem_local_id = `${window.browsergym_frame_id_generator.next()}`;
                }
                // other elements get numerical ids: '0', '1', '2', ...
                else {
                    elem_local_id = `${window.browsergym_elem_counter++}`;
                }
                if (parent_bid == "") {
                    elem_global_bid = `${elem_local_id}`;
                }
                else {
                    elem_global_bid = `${parent_bid}${elem_local_id}`;
                }
                elem.setAttribute(bid_attr_name, `${elem_global_bid}`);
            }
            all_bids.add(elem_global_bid);

            // Hack: store custom data inside ARIA attributes (will be available in DOM and AXTree)
            //  - elem_global_bid: global element identifier (unique over multiple frames)
            push_bid_to_attribute(elem_global_bid, elem, "aria-roledescription");
            push_bid_to_attribute(elem_global_bid, elem, "aria-description");  // fallback for generic nodes

            // set-of-marks flag
            elem.setAttribute("browsergym_set_of_marks", "0");
            // click at center activates self or a child
            if (["self", "child"].includes(whoCapturesCenterClick(elem))) {
                // has valid tag name, or has click event, or triggers a pointer cursor
                if (set_of_marks_tags.has(elem.tagName.toLowerCase()) || (elem.onclick != null) || (window.getComputedStyle(elem).cursor == "pointer")) {
                    let rect = elem.getBoundingClientRect();
                    let area = (rect.right - rect.left) * (rect.bottom - rect.top);
                    // area is large enough
                    if (area >= 20) {
                        // is not a child of a button (role, type, tag) set to be marked
                        if (som_buttons.every(button => !button.contains(elem))) {
                            // is not the sole child of span that has a role and is set to be marked
                            let parent = elem.parentElement;
                            if (!(parent && parent.tagName.toLowerCase() == "span" && parent.children.length === 1 && parent.getAttribute("role") && parent.getAttribute("browsergym_set_of_marks") === "1")) {
                                // all checks have passed, flag the element for inclusion in set-of-marks
                                elem.setAttribute("browsergym_set_of_marks", "1");
                                if (elem.matches('button, a, input[type="button"], div[role="button"]')) {
                                    som_buttons.push(elem)
                                }
                                // lastly, remove the set-of-marks flag from all parents, if any
                                while (parent) {
                                    if (parent.getAttribute("browsergym_set_of_marks") === "1") {
                                        parent.setAttribute("browsergym_set_of_marks", "0")
                                    }
                                    parent = parent.parentElement;
                                }
                            }
                        }
                    }
                }
            }
        }

        warning_msgs = new Array();

        // wait for all elements to be visited for visibility
        let visibility_marking_timeout = 1000;  // ms
        try {
            await until(() => elems_to_be_visited.size == 0, visibility_marking_timeout);
        } catch {
            warning_msgs.push(`Frame marking: not all elements have been visited by the intersection_observer after ${visibility_marking_timeout} ms`);
        }
        // disconnect intersection observer
        intersection_observer.disconnect();

        return warning_msgs;
    }

    async function until(f, timeout, interval=40) {
        return new Promise((resolve, reject) => {
            const start_time = Date.now();
            // immediate check
            if (f()) {
                resolve();
            }
            // loop check
            const wait = setInterval(() => {
                if (f()) {
                    clearInterval(wait);
                    resolve();
                } else if (Date.now() - start_time > timeout) {
                    clearInterval(wait);
                    reject();
                }
            }, interval);
        });
    }


    function whoCapturesCenterClick(element){
        var rect = element.getBoundingClientRect();
        var x = (rect.left + rect.right) / 2 ;
        var y = (rect.top + rect.bottom) / 2 ;
        var element_at_center = elementFromPoint(x, y); // return the element in the foreground at position (x,y)
        if (!element_at_center) {
            return "nobody";
        } else if (element_at_center === element) {
            return "self";
        } else if (element.contains(element_at_center)) {
            return "child";
        } else {
            return "non-descendant";
        }
    }

    function push_bid_to_attribute(bid, elem, attr){
        let original_content = "";
        if (elem.hasAttribute(attr)) {
            original_content = elem.getAttribute(attr);
        }
        let new_content = `browsergym_id_${bid} ${original_content}`
        elem.setAttribute(attr, new_content);
    }

    function elementFromPoint(x, y) {
        let dom = document;
        let last_elem = null;
        let elem = null;

        do {
            last_elem = elem;
            elem = dom.elementFromPoint(x, y);
            dom = elem?.shadowRoot;
        } while(dom && elem !== last_elem);

        return elem;
    }

    // https://stackoverflow.com/questions/12504042/what-is-a-method-that-can-be-used-to-increment-letters#answer-12504061
    class IFrameIdGenerator {
        constructor(chars = 'abcdefghijklmnopqrstuvwxyz') {
          this._chars = chars;
          this._nextId = [0];
        }

        next() {
          const r = [];
          for (let i = 0; i < this._nextId.length; i++) {
            let char = this._chars[this._nextId[i]];
            // all but first character must be upper-cased (a, aA, bCD)
            if (i < this._nextId.length - 1) {
                char = char.toUpperCase();
            }
            r.unshift(char);
          }
          this._increment();
          return r.join('');
        }

        _increment() {
          for (let i = 0; i < this._nextId.length; i++) {
            const val = ++this._nextId[i];
            if (val < this._chars.length) {
              return;
            }
            this._nextId[i] = 0;
          }
          this._nextId.push(0);
        }

        *[Symbol.iterator]() {
          while (true) {
            yield this.next();
          }
        }
      }
    """
    
    # Mark DOM elements with browsergym_id
    await page.evaluate(js_frame_mark_elements, ["", BROWSERGYM_ID_ATTRIBUTE, "standard_html"])
    
    # Extract frame tree
    frame_tree = await cdp.send("Page.getFrameTree", {})
    
    # Extract all frame IDs (breadth-first search)
    frame_ids = []
    root_frame = frame_tree["frameTree"]
    frames_to_process = [root_frame]
    while frames_to_process:
        frame = frames_to_process.pop(0)
        frames_to_process.extend(frame.get("childFrames", []))
        frame_id = frame["frame"]["id"]
        frame_ids.append(frame_id)
    
    # Extract AXTree for each frame
    frame_axtrees = {}
    for frame_id in frame_ids:
        ax_tree = await cdp.send("Accessibility.getFullAXTree", {"frameId": frame_id})
        frame_axtrees[frame_id] = ax_tree
    
    # Extract browsergym IDs from ARIA attributes and add to nodes
    for ax_tree in frame_axtrees.values():
        for node in ax_tree["nodes"]:
            # Look for data in "roledescription" property
            if "properties" in node:
                for prop in node["properties"]:
                    if prop["name"] == "roledescription":
                        value = prop["value"]["value"]
                        if value.startswith("browsergym_id_"):
                            bid = value.split(" ")[0].replace("browsergym_id_", "")
                            node["browsergym_id"] = bid
                            break
            
            # Look for data in "description" property (fallback)
            if "description" in node and not node.get("browsergym_id"):
                value = node["description"]["value"]
                if value.startswith("browsergym_id_"):
                    bid = value.split(" ")[0].replace("browsergym_id_", "")
                    node["browsergym_id"] = bid
    
    # Merge all AXTrees
    merged_axtree = {"nodes": []}
    for ax_tree in frame_axtrees.values():
        merged_axtree["nodes"].extend(ax_tree["nodes"])
    
    # Connect iframes to their content
    for node in merged_axtree["nodes"]:
        if node.get("role", {}).get("value") == "Iframe":
            # Find the frame root node that matches this iframe's frameId
            if "backendDOMNodeId" in node:
                # Get the frameId for this iframe node
                frame_info = await cdp.send("DOM.describeNode", {"backendNodeId": node["backendDOMNodeId"]})
                iframe_frame_id = frame_info.get("node", {}).get("frameId")
                
                if iframe_frame_id in frame_axtrees:
                    # Find the root node of the target frame
                    frame_root_node = frame_axtrees[iframe_frame_id]["nodes"][0]
                    # Link the iframe node to the root node of its content
                    if "childIds" not in node:
                        node["childIds"] = []
                    node["childIds"].append(frame_root_node["nodeId"])
    
    # Clean up by removing any leftover temporary data
    await cdp.detach()
    
    return merged_axtree


async def extract_dom_extra_properties(page: Page, merged_axtree: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Extract additional properties for DOM elements like visibility, bounding box, and clickability
    
    Args:
        page: The Playwright page
        merged_axtree: The merged AXTree from extract_axtree
        
    Returns:
        A dictionary mapping browsergym_ids to their extra properties
    """
    # Get all nodes with browsergym_ids
    nodes_with_bid = {}
    for node in merged_axtree["nodes"]:
        if "browsergym_id" in node:
            nodes_with_bid[node["browsergym_id"]] = node
    
    # Use JavaScript to get the extra properties
    js_get_extra_props = f"""
    () => {{
        const extra_properties = {{}};
        const elements = document.querySelectorAll('[{BROWSERGYM_ID_ATTRIBUTE}]');
        
        for (const elem of elements) {{
            const bid = elem.getAttribute('{BROWSERGYM_ID_ATTRIBUTE}');
            const visibility = parseFloat(elem.getAttribute('{BROWSERGYM_VISIBILITY_ATTRIBUTE}') || "0");
            const set_of_marks = elem.getAttribute('{BROWSERGYM_SETOFMARKS_ATTRIBUTE}') === "1";
            
            // Get bounding box
            let bbox = null;
            const rect = elem.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {{
                bbox = [rect.x, rect.y, rect.width, rect.height];
            }}
            
            // Determine if element is clickable
            const clickable = elem.tagName === 'BUTTON' || 
                             elem.tagName === 'A' || 
                             elem.getAttribute('role') === 'button' ||
                             elem.onclick !== null ||
                             window.getComputedStyle(elem).cursor === 'pointer';
            
            extra_properties[bid] = {{
                visibility,
                bbox,
                clickable,
                set_of_marks
            }};
        }}
        
        return extra_properties;
    }}
    """
    
    extra_properties = await page.evaluate(js_get_extra_props)
    return extra_properties


async def get_observation(page: Page) -> Dict[str, Any]:
    """
    Generate an observation from a page, including AXTree with browsergym_ids
    
    Args:
        page: The Playwright page to observe
        
    Returns:
        A dictionary containing the observation data
    """
    # Extract the AXTree with browsergym_ids
    merged_axtree = await extract_axtree(page)
    
    # Extract extra properties for DOM elements
    extra_properties = await extract_dom_extra_properties(page, merged_axtree)
    
    # Get current URL
    url = page.url
    
    # Create observation object
    observation = {
        "axtree": merged_axtree,
        "extra_properties": extra_properties,
        "url": url
    }
    
    return observation


# Action execution functions
async def noop(page: Page, wait_ms: float = 1000):
    """Wait for a specified amount of time."""
    await page.wait_for_timeout(wait_ms)


async def scroll(page: Page, delta_x: float, delta_y: float):
    """Scroll the page by the specified delta."""
    await page.evaluate(f"window.scrollBy({delta_x}, {delta_y})")


async def fill(page: Page, bid: str, value: str):
    """Fill an input element with text."""
    element = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{bid}']")
    await element.fill(value)


async def select_option(page: Page, bid: str, options: Union[str, List[str]]):
    """Select option(s) in a select element."""
    element = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{bid}']")
    if isinstance(options, str):
        await element.select_option(value=options)
    else:
        await element.select_option(values=options)


async def click(page: Page, bid: str, button: Literal['left', 'middle', 'right'] = 'left', 
               modifiers: List[Literal['Alt', 'Control', 'Meta', 'Shift']] = None):
    """Click on an element."""
    if modifiers is None:
        modifiers = []
    element = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{bid}']")
    await element.click(button=button, modifiers=modifiers)


async def dblclick(page: Page, bid: str, button: Literal['left', 'middle', 'right'] = 'left',
                  modifiers: List[Literal['Alt', 'Control', 'Meta', 'Shift']] = None):
    """Double-click on an element."""
    if modifiers is None:
        modifiers = []
    element = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{bid}']")
    await element.dblclick(button=button, modifiers=modifiers)


async def hover(page: Page, bid: str):
    """Hover over an element."""
    element = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{bid}']")
    await element.hover()


async def press(page: Page, bid: str, key_comb: str):
    """Press a key combination on an element."""
    element = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{bid}']")
    await element.press(key_comb)


async def focus(page: Page, bid: str):
    """Focus on an element."""
    element = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{bid}']")
    await element.focus()


async def clear(page: Page, bid: str):
    """Clear an input element."""
    element = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{bid}']")
    await element.fill("")


async def drag_and_drop(page: Page, from_bid: str, to_bid: str):
    """Drag and drop from one element to another."""
    source = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{from_bid}']")
    target = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{to_bid}']")
    
    source_box = await source.bounding_box()
    target_box = await target.bounding_box()
    
    await page.mouse.move(
        source_box["x"] + source_box["width"] / 2,
        source_box["y"] + source_box["height"] / 2
    )
    await page.mouse.down()
    await page.mouse.move(
        target_box["x"] + target_box["width"] / 2,
        target_box["y"] + target_box["height"] / 2
    )
    await page.mouse.up()


async def upload_file(page: Page, bid: str, file_paths: Union[str, List[str]]):
    """Upload a file to an input element."""
    element = page.locator(f"[{BROWSERGYM_ID_ATTRIBUTE}='{bid}']")
    if isinstance(file_paths, str):
        await element.set_input_files(file_paths)
    else:
        await element.set_input_files(file_paths)


async def goto(page: Page, url: str):
    """Navigate to a URL."""
    await page.goto(url)


async def go_back(page: Page):
    """Navigate back in history."""
    await page.go_back()


async def go_forward(page: Page):
    """Navigate forward in history."""
    await page.go_forward()


async def tab_close(page: Page):
    """Close the current tab."""
    await page.close()


async def tab_focus(page: Page, index: int):
    """Focus on a tab by index."""
    pages = await page.context.pages()
    if 0 <= index < len(pages):
        await pages[index].bring_to_front()


async def new_tab(page: Page, url: Optional[str] = None):
    """Open a new tab with an optional URL."""
    new_page = await page.context.new_page()
    if url:
        await new_page.goto(url)
    return new_page


async def press_key(page: Page, key: str):
    """Press a key without targeting a specific element."""
    await page.keyboard.press(key)


# These are BrowserGym specific actions that would be in functions.py
async def send_msg_to_user(page: Page, text: str):
    """Send a message to the user chat."""
    # In a real environment, this would communicate with the BrowserGym chat system
    print(f"Message to user: {text}")


async def report_infeasible(page: Page, reason: str):
    """Report that the task is infeasible."""
    # In a real environment, this would communicate with the BrowserGym system
    print(f"Task reported as infeasible: {reason}")


async def execute_action(page: Page, action: str) -> Dict[str, Any]:
    """
    Execute a high-level action on a page in the BrowserGym format
    
    Args:
        page: The Playwright page to act on
        action: BrowserGym formatted action string (e.g., "click('123')")
        
    Returns:
        Results including success, error (if any)
    """
    result = {
        "success": False,
        "error": None
    }
    
    # Parse the action string to get the function name and arguments
    try:
        # Extract the function name and argument string from the action string
        if "(" not in action or ")" not in action:
            result["error"] = f"Invalid action format: {action}"
            return result
        
        func_name = action.split("(")[0].strip()
        args_str = action.split("(", 1)[1].rsplit(")", 1)[0]
        
        # Map function name to the implementation
        action_map = {
            'noop': noop,
            'scroll': scroll,
            'fill': fill,
            'select_option': select_option,
            'click': click,
            'dblclick': dblclick,
            'hover': hover,
            'press': press,
            'press_key': press_key,
            'focus': focus,
            'clear': clear,
            'drag_and_drop': drag_and_drop,
            'upload_file': upload_file,
            'goto': goto,
            'go_back': go_back,
            'go_forward': go_forward,
            'tab_close': tab_close,
            'tab_focus': tab_focus,
            'new_tab': new_tab,
            'send_msg_to_user': send_msg_to_user,
            'report_infeasible': report_infeasible
        }
        
        if func_name not in action_map:
            result["error"] = f"Unknown action type: {func_name}"
            return result
        
        # Parse arguments - this is a simplified parser that works for basic cases
        # For more complex cases like nested quotes, a proper parser would be needed
        args = []
        kwargs = {}
        
        if args_str.strip():
            # Split by commas but not within quotes
            in_quote = False
            quote_char = None
            segments = []
            current_segment = ""
            
            for char in args_str:
                if char in ["'", '"'] and (not in_quote or char == quote_char):
                    in_quote = not in_quote
                    quote_char = char if in_quote else None
                    current_segment += char
                elif char == "," and not in_quote:
                    segments.append(current_segment.strip())
                    current_segment = ""
                else:
                    current_segment += char
            
            if current_segment:
                segments.append(current_segment.strip())
            
            # Process each segment
            for segment in segments:
                if "=" in segment and not (segment.startswith("'") or segment.startswith('"')):
                    # This is a keyword argument
                    key, value = segment.split("=", 1)
                    key = key.strip()
                    value = eval(value.strip())  # CAUTION: Using eval for simplicity
                    kwargs[key] = value
                else:
                    # This is a positional argument
                    args.append(eval(segment))  # CAUTION: Using eval for simplicity
        
        # Execute the action
        action_func = action_map[func_name]
        await action_func(page, *args, **kwargs)
        
        # Wait for page to stabilize after action execution
        if func_name not in ['noop', 'send_msg_to_user', 'report_infeasible']:
            await page.wait_for_load_state("networkidle")
            
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def flatten_axtree_to_str(axtree: dict, show_generic_nodes: bool = True) -> str:
    """
    Convert AXTree to a string representation similar to BrowserGym.
    
    Args:
        axtree: The AXTree to format
        show_generic_nodes: If False, hide generic nodes with empty names to reduce clutter
        
    Returns:
        Formatted string representation of the AXTree
    """
    result = []
    
    # Create a map of nodes by id
    nodes_by_id = {}
    for node in axtree["nodes"]:
        if "nodeId" in node:
            nodes_by_id[node["nodeId"]] = node
    
    # Find the root node
    root_node = None
    for node in axtree["nodes"]:
        if "nodeId" in node and "role" in node and node["role"].get("value") == "RootWebArea":
            root_node = node
            break
    
    if not root_node:
        return "No root node found"
    
    def format_node(node, indent=0):
        node_id = node.get("nodeId")
        role = node.get("role", {}).get("value", "unknown")
        name = node.get("name", {}).get("value", "") if "name" in node else ""
        bid = node.get("browsergym_id", "")
        
        # Skip nodes with empty names if show_generic_nodes is False
        if not show_generic_nodes and name == "" and "childIds" in node:
            # Directly process children instead
            for child_id in node["childIds"]:
                if child_id in nodes_by_id:
                    format_node(nodes_by_id[child_id], indent)
            return
        
        properties = []
        
        if "url" in node:
            properties.append(f"url='{node['url']}'")
        
        if "focused" in node and node["focused"].get("value", False):
            properties.append("focused")
        
        for prop in node.get("properties", []):
            prop_name = prop["name"]
            try:
                prop_value = prop["value"]["value"]
                if prop_name not in ["roledescription", "description"]:
                    properties.append(f"{prop_name}='{prop_value}'")
            except (KeyError, TypeError):
                # Skip properties with unexpected structure
                continue
        
        props_text = ", ".join(properties) if properties else ""
        
        # Format the node line
        if bid:
            node_line = f"{' ' * indent}[{bid}] {role} '{name}'"
        else:
            node_line = f"{' ' * indent}{role} '{name}'"
        
        if props_text:
            node_line += f", {props_text}"
        
        result.append(node_line)
        
        # Process children
        if "childIds" in node:
            for child_id in node["childIds"]:
                if child_id in nodes_by_id:
                    format_node(nodes_by_id[child_id], indent + 1)
    
    # Start formatting from the root
    format_node(root_node)
    
    return "\n".join(result)


class BrowserController:
    """
    A controller class for browser automation with accessibility tree extraction
    and high-level action execution following BrowserGym conventions.
    """
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.show_generic_nodes = True  # Default to showing all nodes
        self.headless = True
        
    async def __aenter__(self):
        self.playwright = await async_playwright().__aenter__()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(viewport={"width": 1280, "height": 720})
        self.page = await self.context.new_page()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.browser.close()
        await self.playwright.__aexit__(exc_type, exc_val, exc_tb)
    
    async def goto(self, url: str):
        """Navigate to a URL and wait for the page to load."""
        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')
    
    async def get_observation(self) -> Dict[str, Any]:
        """Get the current page observation with AXTree and extra properties."""
        return await get_observation(self.page)
    
    async def execute_action(self, action: str) -> Dict[str, Any]:
        """Execute a high-level action following BrowserGym conventions."""
        return await execute_action(self.page, action)
    
    async def get_screenshot(self) -> bytes:
        """Get a screenshot of the current page."""
        return await self.page.screenshot()
    
    def format_axtree(self, observation: Dict[str, Any]) -> str:
        """Format the AXTree into a readable text like in BrowserGym logs."""
        return flatten_axtree_to_str(observation["axtree"], show_generic_nodes=self.show_generic_nodes)
    
    def set_show_generic_nodes(self, show: bool):
        """Set whether to show or hide generic nodes in the AXTree output."""
        self.show_generic_nodes = show


async def main():
    parser = argparse.ArgumentParser(description='Browser automation with Playwright in BrowserGym style')
    parser.add_argument('--url', type=str, default='https://evals-udriver.vercel.app/', 
                        help='URL to navigate to (default: https://evals-udriver.vercel.app/)')
    parser.add_argument('--action', type=str, help='Action to execute in BrowserGym format, e.g. "click(\'123\')"')
    parser.add_argument('--hide-generic', action='store_true', help='Hide generic nodes with empty names in AXTree output')
    args = parser.parse_args()
    
    async with BrowserController() as controller:
        # Set display options for AXTree
        controller.set_show_generic_nodes(not args.hide_generic)
        
        # Navigate to URL
        print(f"Navigating to {args.url}...")
        await controller.goto(args.url)
        
        # Get observation
        print("Getting observation...")
        observation = await controller.get_observation()
        
        # Print AXTree in BrowserGym format
        print("\n# Current page Accessibility Tree")
        print(controller.format_axtree(observation))
        
        # If an action was provided, execute it
        if args.action:
            print(f"\nExecuting action: {args.action}")
            result = await controller.execute_action(args.action)
            print(f"Result: {json.dumps(result, indent=2)}")
            
            # Get updated observation after action
            print("\nUpdated observation after action:")
            observation = await controller.get_observation()
            print(controller.format_axtree(observation))
        
        # Interactive mode
        print("\nEnter BrowserGym actions (e.g. \"fill('108', 'Fitness Urbano')\") or special commands:")
        print("- 'show_generic': Show all generic nodes in AXTree output")
        print("- 'hide_generic': Hide generic nodes with empty names in AXTree output")
        print("- 'q': Quit")
        
        while True:
            action = input("> ")
            if action.lower() in ['q', 'quit', 'exit']:
                break
            elif action.lower() == 'show_generic':
                controller.set_show_generic_nodes(True)
                print("Generic nodes will now be shown in AXTree output")
                continue
            elif action.lower() == 'hide_generic':
                controller.set_show_generic_nodes(False)
                print("Generic nodes with empty names will now be hidden in AXTree output")
                continue
                
            result = await controller.execute_action(action)
            print(f"Result: {json.dumps(result, indent=2)}")
            
            # Get updated observation after action
            observation = await controller.get_observation()
            print("\n# Current page Accessibility Tree")
            print(controller.format_axtree(observation))


if __name__ == "__main__":
    asyncio.run(main())