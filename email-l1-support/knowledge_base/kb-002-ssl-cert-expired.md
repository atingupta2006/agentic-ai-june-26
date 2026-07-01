# KB-002: Expired or invalid TLS/SSL certificate

## Symptoms
- Browser shows "Your connection is not private" / NET::ERR_CERT_DATE_INVALID.
- API clients fail with certificate verification errors.
- Issue starts suddenly at a specific date/time (the expiry moment).

## Key error signatures
- `SSL: CERTIFICATE_VERIFY_FAILED certificate has expired`
- `javax.net.ssl.SSLHandshakeException: PKIX path validation failed`
- `curl: (60) SSL certificate problem: certificate has expired`

## Root cause
The server's TLS certificate has expired, or the client does not trust the
issuing CA (missing intermediate certificate).

## Resolution steps
1. Check expiry: `openssl s_client -connect host:443 | openssl x509 -noout -dates`.
2. Renew/reissue the certificate from your CA or ACME provider.
3. Install the full chain (leaf + intermediates), not just the leaf cert.
4. Reload the web server / load balancer to pick up the new cert.
5. Verify from an external client.

## Prevention
- Automate renewal (e.g. ACME / cert-manager) and alert 30 days before expiry.
