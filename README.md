# SPA Renderer

This document provides details on the configuration of the Single Page Application (SPA) Renderer.
All configuration values and their description can be found in [config.yaml](config.yaml).
Variables can either be set directly in [config.yaml](config.yaml), or else, via
environment variables - e.g. `.env` and (for sensitive values) `.env.local` or
via docker's `-e a=b` flags.
> Note: when overriding a config variable from environment, the key must
> be in upper case: e.g. `S3_STORAGE_ENABLE=1`. Complex valuse (e.g. `dict` or `list` types)
> can be specified as jason and be base64 encoded. Example:
> ```bash
> base64 -w0 <<EOF
> [
>  ['body', ['[data-ready="true"]'], 'attached'],
>  ['body', ['[data-test="loading-image"]'], 'detached'],
>  ['.maincolumn-categorypage', ['[data-test="product-item"]'], 'visible']
> ]
> EOF
> >> WwogIFsnYm9keScsIFsnW2RhdGEtcmVhZHk9InRydWUiXSddLCAnYXR0YWNoZWQnXSwKICBbJ2JvZHknLCBbJ1tkYXRhLXRlc3Q9ImxvYWRpbmctaW1hZ2UiXSddLCAnZGV0YWNoZWQnXSwKICBbJy5tYWluY29sdW1uLWNhdGVnb3J5cGFnZScsIFsnW2RhdGEtdGVzdD0icHJvZHVjdC1pdGVtIl0nXSwgJ3Zpc2libGUnXQpdCg==
> READY_CONDITIONS=data:WwogIFsnYm9keScsIFsnW2RhdGEtcmVhZHk9InRydWUiXSddLCAnYXR0YWNoZWQnXSwKICBbJ2JvZHknLCBbJ1tkYXRhLXRlc3Q9ImxvYWRpbmctaW1hZ2UiXSddLCAnZGV0YWNoZWQnXSwKICBbJy5tYWluY29sdW1uLWNhdGVnb3J5cGFnZScsIFsnW2RhdGEtdGVzdD0icHJvZHVjdC1pdGVtIl0nXSwgJ3Zpc2libGUnXQpdCg==
> ```

## Versioning

```yaml
version: '1.0.1'
```

## HTTP Headers

HTTP headers to be sent with each request can be specified in the `extra_http_headers` field.

```yaml
extra_http_headers:
  x-spa-renderer: '${version}'
```

## Readiness Checks

### Network Idleness Check

Wait for background request 'idleness'.

SPA Renderer will keep track of request and response counts for URLs
matching the `network_idle_requests_url_pattern`.
The page is considered ready for scraping when the number of pending requests remains zero
for at least `network_idle_time` milliseconds. If network idleness check is enabled (`network_idle_check: yes`),
Then the [Custom Readiness Conditions](#custom-readiness-conditions) will be evaluated once idleness is reached.
Else, no network idleness check will be done, the page will load and immediately
wait for `network_idle_time` milliseconds, then [Custom Readiness Conditions](#custom-readiness-conditions) will be evaluated.

```yaml
network_idle_requests_url_pattern: '^@BASE_URL@(/|\?|$)'
network_idle_time: 5000
network_idle_check: yes
```

### Custom Readiness Conditions

Defines custom conditions to check if the page is fully loaded and ready by using CSS or XPath selectors.

```yaml
# Defines custom conditions
ready_conditions:
  - ['body', ['[data-ready="true"]'], 'attached']
  - ['body', ['[data-test="loading-image"]'], 'detached']
  - ['.maincolumn-categorypage', ['[data-test="product-item"]'], 'visible']
```

**Format**:
```yaml
- ['<trigger_selector>', ['<selector>'], '<condition>']
```

- **trigger_selector**: CSS/Xpath expression. The presence (as in 'attached')
   of this selector will determine either to evaluate the <selector> conditions. This way
   `ready_conditions` can hold multiple conditions some of
   which will only be relevant to a specific page, while
   others may be ignored. For example, selectors of a condition with `trigger_selector`
   having the value of 'body' will always be checked, whereas if the `trigger_selector`
   is '.maincolumn-categorypage', they will only be checked when on the category page.
   (assuming only your category page has an element with class 'maincolumn-categorypage')
   > Note: this selector test is always for the 'attached' state, regardless of the value of `condition` below.
- **selector**: CSS or XPath selector to match elements.
- **condition**: `attached` for presence, `detached` for absence.

### Elements to Remove

Defines a list of CSS selectors for elements that should be removed before
dumping the DOM.

```yaml
# Elements to remove before processing
remove_elements:
  - '[data-name="cookie-privacy-notice"]'
  - '[data-test="loading-image"]'
  - '#amazon-connect-chat-widget'
  - '.rbBF2Vi9s4OAzzpGtfkMwA\\=\\='
```

**Format**:
```yaml
- '<selector>'
```

* selector: CSS selector (Xpath not supported)

## Screen Configuration

Defines screen dimensions for rendering.

```yaml
screen: 1280x1024
screen_presets:
  mobile: 411x731
  nexus5: 412x732
  desktop: 1200x1024
  iphone: 390x850
```

## User Agent Mapping

Maps user agents to screen presets.

```yaml
user_agent_screen_mapping:
  -
    - iphone
    - iphone
  -
    - nexus
    - nexus5
  -
    - iphone
    - iphone
  -
    - mobile
    - mobile
```

## Timeout Configuration

Defines the default timeout (in milliseconds) for rendering.

```yaml
default_timeout: 20000
```

## User Agent

Defines the user agent string and any additional strings to append.

```yaml
user_agent: ''
user_agent_append: ChefworksPrerender
default_user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.3"
```

* **user_agent**: Tell SPA Renderer what user agent to consider for resolving viewport etc.
* **user_agent_append**: Always append this string to the end of the user agent SPA Render will use in requests to your site.
* **default_user_agent**: Fallback to this user agent if the API client did not provide one

## Device Configuration

Defines any specific device configurations.

```yaml
device: ''
```

## Debug Mode

Enable or disable debug mode.

Debugging is only useful when running SPA Renderer locally,
as it will open the chromium window and give you a chance to see what the page looks like during
rendering.

```yaml
debug: no
```

## Base URL

Enable or disable base URL addition.

Add `<base href="<your-request-url>" />` to html/head, so the page
styling and images will show correctly even if the page is viewed
from a downloaded file or from a hosted S3 cache repository.

```yaml
add_base_url: yes
```

## Preload Pages

Enable or disable page preloading.

Sometime open the page then immediately closing it, then reopening it 2nd time and processing
it fully may give less page loading errors.

```yaml
preload_pages: no
```

## Retry Configuration

Defines the number of retry attempts.

```yaml
max_tries: 2
```

## S3 Storage Configuration

Configuration settings for storing pages in an Amazon S3 bucket.

The access/secret keys should not be placed in [config.yaml](config.yaml) for
security reasons. Put them in `.env.local` or configure via docker environment variables
or K8S secrets.

```yaml
# Set `store_pages: yes` to enable page storage in S3
store_pages: no
s3_endpoint: ''
s3_bucket_name: ''
s3_access_key: ''
s3_secret_key: ''
```

- **s3_endpoint**: Custom S3 endpoint URL (if any).
- **s3_bucket_name**: Name of the S3 bucket.
- **s3_access_key**: Access key for S3 authentication.
- **s3_secret_key**: Secret key for S3 authentication.
