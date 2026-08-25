/* Fluér de Luné — global behaviours
   (Alpine components live in alpine-init.js, which must load before the
   Alpine.js CDN script.) */

/* ===== Confirmation modal =====
   Replaces the browser's native confirm() for htmx actions carrying
   `data-confirm-modal`. The question text comes from hx-confirm; accepting
   issues the original request. */
(function () {
    'use strict';

    var modal, questionEl, pendingRequest = null;

    function openModal(question, issueRequest) {
        if (!modal) return;
        pendingRequest = issueRequest;
        questionEl.textContent = question || 'Are you sure?';
        modal.classList.add('is-open');
        document.body.classList.add('scroll-lock');
        var accept = modal.querySelector('[data-fdl-confirm-accept]');
        if (accept) accept.focus();
    }

    function closeModal() {
        if (!modal) return;
        pendingRequest = null;
        modal.classList.remove('is-open');
        document.body.classList.remove('scroll-lock');
    }

    document.addEventListener('DOMContentLoaded', function () {
        modal = document.getElementById('fdl-confirm');
        if (!modal) return;

        document.addEventListener('htmx:confirm', function (e) {
            var elt = e.detail && e.detail.elt;
            if (!(elt instanceof Element) || !elt.hasAttribute('data-confirm-modal')) {
                return; // let unmarked actions use native behaviour
            }
            e.preventDefault();
            var question = elt.getAttribute('hx-confirm') || e.detail.question;
            openModal(question, function () { e.detail.issueRequest(true); });
        });

        modal.addEventListener('click', function (e) {
            if (e.target.closest('[data-fdl-confirm-accept]')) {
                var issue = pendingRequest;
                closeModal();
                if (issue) issue();
            } else if (e.target.closest('[data-fdl-confirm-cancel]') || e.target === modal.querySelector('.modal__backdrop')) {
                closeModal();
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && modal.classList.contains('is-open')) closeModal();
        });
    });
})();

/* ===== Dark mode toggle =====
   Manual choice persists; otherwise follows the device theme live. */
(function () {
    'use strict';

    var THEME_KEY = 'fdl-theme';
    var root = document.documentElement;

    function systemTheme() {
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light';
    }

    function storedTheme() {
        try {
            return localStorage.getItem(THEME_KEY);
        } catch (e) {
            return null;
        }
    }

    function applyTheme(theme) {
        root.setAttribute('data-theme', theme);
        var meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.setAttribute('content', theme === 'dark' ? '#201b16' : '#c9a962');
        }
    }

    applyTheme(storedTheme() === 'dark' || storedTheme() === 'light' ? storedTheme() : systemTheme());

    document.addEventListener('DOMContentLoaded', function () {
        var btn = document.getElementById('theme-toggle');
        if (!btn) return;
        btn.addEventListener('click', function () {
            var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            applyTheme(next);
            try {
                localStorage.setItem(THEME_KEY, next);
            } catch (e) { /* private mode */ }
        });
    });

    if (window.matchMedia) {
        var mq = window.matchMedia('(prefers-color-scheme: dark)');
        var onChange = function (e) {
            if (!storedTheme()) {
                applyTheme(e.matches ? 'dark' : 'light');
            }
        };
        if (mq.addEventListener) mq.addEventListener('change', onChange);
        else if (mq.addListener) mq.addListener(onChange);
    }
})();
