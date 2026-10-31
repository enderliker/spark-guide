/* Spark Guide — client-side behaviour: theme, navigation, search and copy. */
(function () {
  "use strict";

  var doc = document;
  var html = doc.documentElement;

  /* ---------------------------------------------------------------------
   * Theme
   * ------------------------------------------------------------------- */
  var themeButton = doc.getElementById("theme-toggle");

  function currentTheme() {
    return html.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function applyTheme(theme) {
    html.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("spark-theme", theme);
    } catch (error) {
      /* storage may be unavailable; the theme still applies */
    }
    if (themeButton) {
      themeButton.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
      );
    }
  }

  if (themeButton) {
    applyTheme(currentTheme());
    themeButton.addEventListener("click", function () {
      applyTheme(currentTheme() === "dark" ? "light" : "dark");
    });
  }

  /* ---------------------------------------------------------------------
   * Mobile sidebar
   * ------------------------------------------------------------------- */
  var menuButton = doc.getElementById("menu-toggle");
  var backdrop = doc.getElementById("backdrop");
  var sidebar = doc.getElementById("sidebar");

  function setSidebar(open) {
    doc.body.classList.toggle("sidebar-open", open);
    if (backdrop) {
      backdrop.hidden = !open;
    }
    if (menuButton) {
      menuButton.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }

  if (menuButton) {
    menuButton.addEventListener("click", function () {
      setSidebar(!doc.body.classList.contains("sidebar-open"));
    });
  }

  if (backdrop) {
    backdrop.addEventListener("click", function () {
      setSidebar(false);
    });
  }

  if (sidebar) {
    sidebar.addEventListener("click", function (event) {
      if (event.target.closest("a") && window.matchMedia("(max-width: 960px)").matches) {
        setSidebar(false);
      }
    });
  }

  /* ---------------------------------------------------------------------
   * Copy code
   * ------------------------------------------------------------------- */
  doc.querySelectorAll(".copy-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      var block = button.closest(".code-block");
      var code = block ? block.querySelector("pre code") : null;
      if (!code) {
        return;
      }
      var text = code.innerText;
      var label = button.querySelector("span");

      function done() {
        if (label) {
          label.textContent = "Copied";
        }
        button.classList.add("copied");
        window.setTimeout(function () {
          if (label) {
            label.textContent = "Copy";
          }
          button.classList.remove("copied");
        }, 1600);
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, fallback);
      } else {
        fallback();
      }

      function fallback() {
        var area = doc.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.opacity = "0";
        doc.body.appendChild(area);
        area.select();
        try {
          doc.execCommand("copy");
          done();
        } catch (error) {
          /* nothing else to try */
        }
        doc.body.removeChild(area);
      }
    });
  });

  /* ---------------------------------------------------------------------
   * Table of contents scroll spy
   * ------------------------------------------------------------------- */
  var tocLinks = Array.prototype.slice.call(doc.querySelectorAll(".toc-list a"));
  var headings = Array.prototype.slice.call(
    doc.querySelectorAll(".page-content h2[id], .page-content h3[id]")
  );

  function setActiveToc(id) {
    tocLinks.forEach(function (link) {
      link.classList.toggle("active", link.getAttribute("href") === "#" + id);
    });
  }

  function updateToc() {
    if (!headings.length) {
      return;
    }
    var offset = 100;
    var active = headings[0];
    for (var i = 0; i < headings.length; i += 1) {
      if (headings[i].getBoundingClientRect().top <= offset) {
        active = headings[i];
      } else {
        break;
      }
    }
    if (active) {
      setActiveToc(active.id);
    }
  }

  if (headings.length && tocLinks.length) {
    var ticking = false;
    window.addEventListener(
      "scroll",
      function () {
        if (!ticking) {
          ticking = true;
          window.requestAnimationFrame(function () {
            updateToc();
            ticking = false;
          });
        }
      },
      { passive: true }
    );
    updateToc();
  }

  /* ---------------------------------------------------------------------
   * Search
   * ------------------------------------------------------------------- */
  var input = doc.getElementById("search-input");
  var resultsBox = doc.getElementById("search-results");
  var index = window.SPARK_SEARCH_INDEX || [];
  var activeResult = -1;
  var visibleResults = [];

  function normalize(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function highlight(text, terms) {
    var safe = escapeHtml(text);
    terms.forEach(function (term) {
      if (!term) {
        return;
      }
      var pattern = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      safe = safe.replace(new RegExp("(" + pattern + ")", "gi"), "<mark>$1</mark>");
    });
    return safe;
  }

  function snippetFor(text, terms) {
    var lower = normalize(text);
    var position = -1;
    for (var i = 0; i < terms.length; i += 1) {
      var found = lower.indexOf(terms[i]);
      if (found !== -1 && (position === -1 || found < position)) {
        position = found;
      }
    }
    if (position === -1) {
      return text.slice(0, 130) + (text.length > 130 ? "…" : "");
    }
    var start = Math.max(0, position - 50);
    var end = Math.min(text.length, position + 110);
    return (
      (start > 0 ? "…" : "") +
      text.slice(start, end).trim() +
      (end < text.length ? "…" : "")
    );
  }

  function search(query) {
    var terms = normalize(query).split(/\s+/).filter(Boolean);
    if (!terms.length) {
      return [];
    }
    var results = [];
    index.forEach(function (page) {
      var title = normalize(page.title);
      var section = normalize(page.section);
      var description = normalize(page.description);
      var headingText = normalize(
        page.headings.map(function (heading) {
          return heading.text;
        }).join(" ")
      );
      var body = normalize(page.text);
      var haystack = title + " " + section + " " + description + " " + headingText + " " + body;

      var score = 0;
      var allPresent = true;
      terms.forEach(function (term) {
        if (haystack.indexOf(term) === -1) {
          allPresent = false;
          return;
        }
        if (title.indexOf(term) !== -1) {
          score += 14;
        }
        if (headingText.indexOf(term) !== -1) {
          score += 7;
        }
        if (description.indexOf(term) !== -1) {
          score += 4;
        }
        score += Math.min(body.split(term).length - 1, 6);
      });
      if (!allPresent) {
        return;
      }
      if (title.indexOf(terms.join(" ")) !== -1) {
        score += 20;
      }

      var anchor = "";
      for (var h = 0; h < page.headings.length; h += 1) {
        var heading = page.headings[h];
        var normalizedHeading = normalize(heading.text);
        var matches = terms.every(function (term) {
          return normalizedHeading.indexOf(term) !== -1;
        });
        if (matches) {
          anchor = "#" + heading.id;
          break;
        }
      }

      results.push({
        page: page,
        score: score,
        anchor: anchor,
        snippet: snippetFor(page.text || page.description, terms)
      });
    });

    results.sort(function (a, b) {
      return b.score - a.score || a.page.title.localeCompare(b.page.title);
    });
    return results.slice(0, 10);
  }

  function renderResults(query) {
    if (!resultsBox) {
      return;
    }
    var terms = normalize(query).split(/\s+/).filter(Boolean);
    if (!terms.length) {
      resultsBox.hidden = true;
      input.setAttribute("aria-expanded", "false");
      activeResult = -1;
      visibleResults = [];
      return;
    }

    var results = search(query);
    visibleResults = results;
    activeResult = results.length ? 0 : -1;

    if (!results.length) {
      resultsBox.innerHTML =
        '<p class="search-empty">No results for “' + escapeHtml(query) + '”</p>';
    } else {
      resultsBox.innerHTML = results
        .map(function (result, index) {
          var page = result.page;
          return (
            '<a class="search-result' +
            (index === 0 ? " active" : "") +
            '" href="' +
            page.url +
            result.anchor +
            '">' +
            '<span class="search-result__meta">' +
            '<span class="search-result__title">' +
            highlight(page.title, terms) +
            "</span>" +
            '<span class="search-result__section">' +
            escapeHtml(page.section) +
            "</span>" +
            "</span>" +
            '<p class="search-result__snippet">' +
            highlight(result.snippet, terms) +
            "</p>" +
            "</a>"
          );
        })
        .join("");
    }

    resultsBox.hidden = false;
    input.setAttribute("aria-expanded", "true");
  }

  function moveActive(delta) {
    if (!visibleResults.length) {
      return;
    }
    activeResult = (activeResult + delta + visibleResults.length) % visibleResults.length;
    var nodes = resultsBox.querySelectorAll(".search-result");
    nodes.forEach(function (node, index) {
      node.classList.toggle("active", index === activeResult);
    });
    var active = nodes[activeResult];
    if (active) {
      active.scrollIntoView({ block: "nearest" });
    }
  }

  if (input && resultsBox) {
    var urlRoot = (function () {
      var script = doc.querySelector('script[src$="assets/js/app.js"]');
      if (!script) {
        return "";
      }
      return script.getAttribute("src").replace("assets/js/app.js", "");
    })();

    input.addEventListener("input", function () {
      renderResults(input.value);
    });

    input.addEventListener("focus", function () {
      if (input.value.trim()) {
        renderResults(input.value);
      }
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        moveActive(1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        moveActive(-1);
      } else if (event.key === "Enter") {
        if (activeResult >= 0 && visibleResults[activeResult]) {
          event.preventDefault();
          var result = visibleResults[activeResult];
          window.location.href = urlRoot + result.page.url + result.anchor;
        }
      } else if (event.key === "Escape") {
        resultsBox.hidden = true;
        input.setAttribute("aria-expanded", "false");
        input.blur();
      }
    });

    doc.addEventListener("click", function (event) {
      if (!event.target.closest("#search")) {
        resultsBox.hidden = true;
        input.setAttribute("aria-expanded", "false");
      }
    });

    doc.addEventListener("keydown", function (event) {
      var typing =
        event.target &&
        (event.target.tagName === "INPUT" ||
          event.target.tagName === "TEXTAREA" ||
          event.target.isContentEditable);

      if (
        (event.key === "k" || event.key === "K") &&
        (event.metaKey || event.ctrlKey)
      ) {
        event.preventDefault();
        input.focus();
        input.select();
        return;
      }

      if (event.key === "/" && !typing) {
        event.preventDefault();
        input.focus();
        input.select();
        return;
      }

      if (event.key === "Escape") {
        setSidebar(false);
      }
    });
  }
})();