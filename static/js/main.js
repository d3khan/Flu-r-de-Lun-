/* Fluér de Luné — Alpine components & global behaviours */
(function () {
    'use strict';

    document.addEventListener('alpine:init', function () {
        Alpine.data('app', function () {
            return {
                mobileMenuOpen: false,
                cartDrawerOpen: false,
                searchOpen: false,
                toasts: [],
                toastSeq: 0,
                cartCount: 0,
                wishlistCount: 0,

init: function () {
                    var self = this;

                    /* Views emit HX-Trigger: cartUpdated after cart mutations */
                    document.body.addEventListener('cartUpdated', function () {
                        self.refreshCounts();
                    });

                    /* Wishlist heart buttons dispatch this with { count } */
                    document.body.addEventListener('wishlist-count', function (e) {
                        if (e.detail && typeof e.detail.count !== 'undefined') {
                            self.wishlistCount = e.detail.count;
                        }
                    });

                    /* Open the drawer whenever its full content is swapped in
                       (add-to-cart / move-to-cart target #cart-drawer). */
                    document.body.addEventListener('htmx:afterSwap', function (e) {
                        if (
                            e.detail.target &&
                            e.detail.target.id === 'cart-drawer' &&
                            e.detail.successful &&
                            !self.cartDrawerOpen
                        ) {
                            self.cartDrawerOpen = true;
                        }
                    });

                    document.addEventListener('keydown', function (e) {
                        if (e.key === 'Escape') self.closeAll();
                    });

                    /* Periodic count refresh (every 500ms) */
                    self._countRefreshInterval = setInterval(function () {
                        self.refreshCounts();
                    }, 500);
                },

                openCart: function () {
                    this.cartDrawerOpen = true;
                },

                closeAll: function () {
                    this.mobileMenuOpen = false;
                    this.cartDrawerOpen = false;
                    this.searchOpen = false;
                    if (this._countRefreshInterval) {
                        clearInterval(this._countRefreshInterval);
                    }
                },

                addToast: function (message, type) {
                    var id = ++this.toastSeq;
                    this.toasts.push({ id: id, message: message, type: type || 'info' });
                    var self = this;
                    setTimeout(function () {
                        self.removeToast(id);
                    }, 4500);
                },

                removeToast: function (id) {
                    this.toasts = this.toasts.filter(function (t) {
                        return t.id !== id;
                    });
                },

                refreshCounts: function () {
                    var self = this;
                    fetch('/cart/count/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                        .then(function (r) { return r.json(); })
                        .then(function (d) { self.cartCount = d.count; })
                        .catch(function () {});

                    if (String(document.body.dataset.authenticated) === 'true') {
                        fetch('/wishlist/count/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                            .then(function (r) { return r.json(); })
                            .then(function (d) { self.wishlistCount = d.count; })
                            .catch(function () {});
                    }
                },
            };
        });
    });

    /* Expose a tiny helper used by templates that need Alpine outside x-data */
    window.fdlBodyData = function () {
        if (window.Alpine && document.body._x_dataStack) {
            return window.Alpine.$data(document.body);
        }
        return null;
    };
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
