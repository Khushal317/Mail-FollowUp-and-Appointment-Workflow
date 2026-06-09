(function () {
    const strip = document.createElement("div");
    strip.className = "contact-strip";
    strip.innerHTML = `
        <span>Need this service for your business?</span>
        <a href="https://twitter.com/khushal1504" target="_blank" rel="noopener">DM me on Twitter</a>
        <span>or</span>
        <a href="mailto:khushalboy15@gmail.com?subject=Lead%20Automation%20Service%20Inquiry&body=Hi%20Khushal%2C%0A%0AI%20am%20interested%20in%20the%20lead%20automation%20service.%20Here%20are%20my%20contact%20details%3A%0AWhatsApp%3A%20%0AEmail%3A%20%0A">email me</a>
        <span>with your WhatsApp number or email.</span>
        <a class="contact-page-link" href="/contact">Contact page</a>
    `;

    const style = document.createElement("style");
    style.textContent = `
        .contact-strip {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 9999;
            min-height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            flex-wrap: wrap;
            padding: 8px 14px;
            background: #fff8df;
            border-bottom: 1px solid #f1d27a;
            color: #3f3420;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 14px;
            line-height: 1.35;
            box-shadow: 0 8px 20px rgba(33, 45, 70, 0.08);
        }
        .contact-strip a {
            color: #174ebd;
            font-weight: 800;
            text-decoration: none;
        }
        .contact-strip a:hover {
            text-decoration: underline;
        }
        .contact-strip .contact-page-link {
            margin-left: 4px;
            color: #087443;
        }
    `;

    document.head.appendChild(style);

    const originalPadding = window.getComputedStyle(document.body).paddingTop;
    document.body.style.paddingTop = `calc(${originalPadding} + 56px)`;
    document.body.prepend(strip);
})();
