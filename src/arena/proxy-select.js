// REPLACEMENTS
// .ownerDocument with .ownerDocument
// .parentNode with .parentNode
// .target with .target

(function () {
    //noprotect
    var dropdownDiv = null;

    function getDropdownDiv(selectNode) {
        if (dropdownDiv) {
            attachDropdownToSelect(selectNode);
            return dropdownDiv;
        }
        dropdownDiv = document.createElement("DIV");
        dropdownDiv.className = "cb-pvt-dropdown";

        dropdownDiv.addEventListener(
            "mouseup",
            function (e) {
                if (e.target.className.indexOf("cb-pvt-option") >= 0) {
                    var option = e.target;
                    var selectNode = dropdownDiv.selectNode;
                    selectNode.value = option.getAttribute("data-value");

                    var evt = new Event("change", {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                    });
                    selectNode.dispatchEvent(evt);

                    hideDropdown();
                }
            },
            false,
        );

        attachDropdownToSelect(selectNode);
        return dropdownDiv;
    }

    function attachDropdownToSelect(selectNode) {
        if (!selectNode || !selectNode.parentNode) {
            return;
        }
        var parent = selectNode.parentNode;
        if (dropdownDiv.parentNode === parent) {
            return;
        }
        if (window.getComputedStyle(parent).position === "static") {
            parent.style.position = "relative";
        }
        if (dropdownDiv.parentNode) {
            dropdownDiv.parentNode.removeChild(dropdownDiv);
        }
        if (selectNode.nextSibling) {
            parent.insertBefore(dropdownDiv, selectNode.nextSibling);
        } else {
            parent.appendChild(dropdownDiv);
        }
    }

    function isDropdownHidden() {
        if (!dropdownDiv) {
            return true;
        }
        var displayStyle = dropdownDiv.style.display;
        if (displayStyle != null && displayStyle.toUpperCase() === "NONE") {
            return true;
        }
        return false;
    }

    function copyStylesFromSelectNode() {
        var selectNode = dropdownDiv.selectNode;
        var selectNodeCS = window.getComputedStyle(selectNode);
        dropdownDiv.style.fontFamily = selectNodeCS.fontFamily;
        dropdownDiv.style.fontSize = selectNodeCS.fontSize;
    }

    function positionDropdownDiv() {
        var selectNode = dropdownDiv.selectNode;

        dropdownDiv.style.display = "block";
        dropdownDiv.style.zIndex = "20001";

        var selectRect = selectNode.getBoundingClientRect();
        var vpRect = { height: window.innerHeight, width: window.innerWidth };
        var parentRect = dropdownDiv.parentNode
            ? dropdownDiv.parentNode.getBoundingClientRect()
            : { top: 0, left: 0, height: vpRect.height, width: vpRect.width };

        var firstOption = dropdownDiv.children[0];
        var optionHeight = 15; // default height when no option present

        if (firstOption) {
            optionHeight = firstOption.getBoundingClientRect().height;
        }

        dropdownDiv.style.maxHeight = optionHeight * 20 + 2 + "px";
        dropdownDiv.style.maxWidth = vpRect.width - 30 + "px";
        dropdownDiv.style.minWidth = selectRect.width + "px";

        var dropdownRect = dropdownDiv.getBoundingClientRect();

        // determine whether there is more space at the bottom or at the top
        var spaceAtBottom = vpRect.height - selectRect.bottom;
        var spaceAtTop = selectRect.top;
        var spaceAtLeft = selectRect.left + selectRect.width;
        var spaceAtRight = vpRect.width - selectRect.left;

        var outPosition = {};

        dropdownDiv.style.bottom = "";
        dropdownDiv.style.right = "";

        var topPosition = selectRect.bottom - parentRect.top;
        if (dropdownRect.height > spaceAtBottom && spaceAtTop > spaceAtBottom) {
            topPosition =
                selectRect.top - parentRect.top - dropdownRect.height;
            if (topPosition < 0) {
                topPosition = 0;
            }
        }
        dropdownDiv.style.top = topPosition + "px";

        var leftPosition = selectRect.left - parentRect.left;
        if (dropdownRect.width + 20 > spaceAtRight && spaceAtLeft > spaceAtRight) {
            leftPosition =
                selectRect.right - parentRect.left - dropdownRect.width;
            if (leftPosition < 0) {
                leftPosition = 0;
            }
        }
        dropdownDiv.style.left = leftPosition + "px";
    }

    function scrollToSelected() {
        var hasScrollbar = dropdownDiv.scrollHeight > dropdownDiv.clientHeight;
        if (hasScrollbar) {
            var selectedOption = dropdownDiv.querySelector(".cb-pvt-selected");
            if (selectedOption) {
                dropdownDiv.scrollTop = selectedOption.offsetTop;
                // Reason for adding this here is quite odd
                // The event will get appended before DOMMutation call gets through meaning this will become unplayable
                // as the DIV with that ID will not be there
                setTimeout(function () {
                    var evt = document.createEvent("CustomEvent");
                    evt.initEvent("screenjsscroll", true, true);
                    dropdownDiv.dispatchEvent(evt);
                }, 0);
            }
        }
    }

    var mousedownHideDropdownHandler,
        hoverOptionHandler,
        scrollHideDropdownHandler,
        mousewheelDropdownHandler,
        focusHideDropdownHandler,
        changeUpdateDropdownHandler;

    function showDropdown() {
        copyStylesFromSelectNode();
        positionDropdownDiv();
        scrollToSelected();
        var ownerDocument =
            (dropdownDiv.selectNode && dropdownDiv.selectNode.ownerDocument) ||
            document;
        mousedownHideDropdownHandler = function (e) {
            if (dropdownDiv == e.target || dropdownDiv.contains(e.target)) {
                return;
            }
            if (
                dropdownDiv.selectNode === e.target ||
                dropdownDiv.selectNode.contains(e.target)
            ) {
                return;
            }
            if (!isDropdownHidden()) {
                hideDropdown();
            }
        };
        ownerDocument.addEventListener(
            "mousedown",
            mousedownHideDropdownHandler,
            true,
        );
        scrollHideDropdownHandler = function (e) {
            if (dropdownDiv == e.target || dropdownDiv.contains(e.target)) {
                return;
            }
            if (!isDropdownHidden()) {
                hideDropdown();
            }
        };
        ownerDocument.addEventListener(
            "scroll",
            scrollHideDropdownHandler,
            true,
        );
        mousewheelDropdownHandler = function (e) {
            if (
                (e.deltaY > 0 &&
                    dropdownDiv.scrollHeight <=
                        dropdownDiv.scrollTop + dropdownDiv.clientHeight) ||
                (e.deltaY < 0 && dropdownDiv.scrollTop == 0)
            ) {
                e.preventDefault();
            }
        };
        dropdownDiv.addEventListener(
            "mousewheel",
            mousewheelDropdownHandler,
            true,
        );
        hoverOptionHandler = function (e) {
            var target = e.target;
            if (target.className.indexOf("cb-pvt-option") >= 0) {
                var selectedOption =
                    dropdownDiv.querySelector(".cb-pvt-selected");
                selectedOption.className = selectedOption.className.replace(
                    " cb-pvt-selected",
                    "",
                );
                target.className += " cb-pvt-selected";
            }
        };
        dropdownDiv.addEventListener("mouseenter", hoverOptionHandler, true);
        focusHideDropdownHandler = function (e) {
            var selectNode = dropdownDiv.selectNode;
            if (e.target != selectNode && !dropdownDiv.contains(e.target)) {
                hideDropdown();
            }
        };
        ownerDocument.addEventListener("focus", focusHideDropdownHandler, true);
        changeUpdateDropdownHandler = function (e) {
            var selectNode = dropdownDiv.selectNode;
            var updatedValue = selectNode.value;
            var selectedOption = dropdownDiv.querySelector(".cb-pvt-selected");
            if (selectedOption) {
                selectedOption.className = selectedOption.className.replace(
                    " cb-pvt-selected",
                    "",
                );
            }
            var newSelectedOption = dropdownDiv.querySelector(
                ".cb-pvt-option[data-value='" + updatedValue + "']",
            );
            if (newSelectedOption) {
                newSelectedOption.className += " cb-pvt-selected";
                // TODO: This causes multiple scroll events
                // in normal circumstances.
                // I believe this handler is there for changes using keyboard
                scrollToSelected();
            }
        };
        dropdownDiv.selectNode.addEventListener(
            "change",
            changeUpdateDropdownHandler,
            false,
        );
    }

    function hideDropdown() {
        dropdownDiv.style.display = "none";
        var ownerDocument =
            (dropdownDiv.selectNode && dropdownDiv.selectNode.ownerDocument) ||
            document;
        ownerDocument.removeEventListener(
            "mousedown",
            mousedownHideDropdownHandler,
            true,
        );
        ownerDocument.removeEventListener(
            "scroll",
            scrollHideDropdownHandler,
            true,
        );
        dropdownDiv.removeEventListener(
            "scroll",
            mousewheelDropdownHandler,
            true,
        );
        dropdownDiv.removeEventListener("mouseenter", hoverOptionHandler, true);
        ownerDocument.removeEventListener(
            "focus",
            focusHideDropdownHandler,
            true,
        );
        dropdownDiv.selectNode.removeEventListener(
            "change",
            changeUpdateDropdownHandler,
            false,
        );
        if (dropdownDiv.parentNode) {
            dropdownDiv.parentNode.removeChild(dropdownDiv);
        }
        dropdownDiv = undefined;
    }

    function openDropdown(selectNode) {
        if (!isDropdownHidden()) {
            return;
        }
        var dropdownDiv = getDropdownDiv(selectNode);
        dropdownDiv.innerHTML = "";
        dropdownDiv.selectNode = selectNode;

        for (var i = 0, len = selectNode.options.length; i < len; i++) {
            var option = selectNode.options[i];
            var optionSpan = document.createElement("SPAN");
            optionSpan.setAttribute("data-value", option.value);
            optionSpan.setAttribute("data-text", option.text);
            optionSpan.textContent = option.text;
            optionSpan.className = "cb-pvt-option";
            if (option.selected) {
                optionSpan.className += " cb-pvt-selected";
            }
            dropdownDiv.appendChild(optionSpan);
        }
        showDropdown();
    }

    function proxifySelect(selectNode) {
        if (selectNode.hasAttribute("no-proxy-select")) {
            return false;
        }
        if (selectNode.hasAttribute("multiple")) {
            return;
        }
        if (selectNode.hasProxified) return;
        selectNode.hasProxified = true;
        selectNode.addEventListener("mousedown", function (e) {
            e.preventDefault();
            openDropdown(selectNode);
        });

        selectNode.addEventListener("keydown", function (e) {
            if (e.keyCode == 13 || e.keyCode == 32) {
                if (isDropdownHidden()) {
                    e.preventDefault();
                    openDropdown(selectNode);
                } else {
                    e.preventDefault();
                    hideDropdown();
                }
            }
        });
    }

    var hasInitialized = false;

    function initializeProxySelects() {
        if (hasInitialized) {
            return;
        }
        hasInitialized = true;
        var selectNodes = document.getElementsByTagName("select");
        for (var i = 0, len = selectNodes.length; i < len; i++) {
            var selectNode = selectNodes[i];
            proxifySelect(selectNode);
        }
        proxifyDynamicallyAddedSelects();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            initializeProxySelects();
        });
    } else {
        initializeProxySelects();
    }

    //********************************
    // Observe changes happening later in the DOM
    //********************************
    // PERF: Check for performance implications of following
    // select the target node
    function proxifyDynamicallyAddedSelects() {
        var target = document.documentElement;

        // create an observer instance
        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type == "childList") {
                    var added = mutation.addedNodes;
                    var newNode;
                    for (var i = 0; i < added.length; i++) {
                        if ((newNode = added[i]).nodeName == "SELECT") {
                            proxifySelect(newNode);
                        } else if (
                            newNode.childElementCount > 0 &&
                            newNode.querySelectorAll
                        ) {
                            var childIframes =
                                newNode.querySelectorAll("select");
                            for (var j = 0; j < childIframes.length; j++) {
                                var select = childIframes[j];
                                proxifySelect(select);
                            }
                        }
                    }
                }
            });
        });

        // configuration of the observer:
        var config = {
            // attributes: true,
            // attributeFilter: [],
            childList: true,
            subtree: true,
        };

        // pass in the target node, as well as the observer options
        observer.observe(target, config);

        // later, you can stop observing
        // observer.disconnect();
    }
    //********************************
    // Observe changes happening later in the DOM ENDS HERE
    //********************************
})();
