/* Fluér de Luné — Alpine bootstrap
   This file MUST be loaded BEFORE the Alpine.js CDN script (both use
   `defer`, so document order is preserved). It registers all Alpine
   components during `alpine:init` and bridges HTMX-swapped content into
   Alpine, eliminating "app is not defined" / uninitialised-directive
   console errors. */
(function () {
    'use strict';

    /* Guard: this file must run before Alpine boots (both deferred, so
       document order decides). The check below only trips if someone
       loads this file after Alpine without `defer`. */
    var alpineBooted = !!window.Alpine;

    function registerComponents() {
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

                    /* Keep header counts fresh */
                    self.refreshCounts();
                    self._countRefreshInterval = setInterval(function () {
                        self.refreshCounts();
                    }, 5000);
                },

                openCart: function () {
                    this.cartDrawerOpen = true;
                },

                closeAll: function () {
                    this.mobileMenuOpen = false;
                    this.cartDrawerOpen = false;
                    this.searchOpen = false;
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
                }
            };
        });
    }

    if (alpineBooted) {
        /* Alpine already booted (edge case): register immediately and
           re-initialise so directives pick the component up. */
        registerComponents();
        window.Alpine.initTree(document.body);
    } else {
        /* Normal path: register while Alpine boots. */
        document.addEventListener('alpine:init', registerComponents);
    }

    /* Bridge: initialise Alpine directives inside HTMX-swapped content
       (cart drawer, quick view modal, etc.) as soon as it lands. */
    ['htmx:afterSwap', 'htmx:oobAfterSwap'].forEach(function (evt) {
        document.addEventListener(evt, function (e) {
            if (window.Alpine && e.detail && e.detail.target) {
                try {
                    window.Alpine.initTree(e.detail.target);
                } catch (err) { /* already initialised — safe to ignore */ }
            }
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
