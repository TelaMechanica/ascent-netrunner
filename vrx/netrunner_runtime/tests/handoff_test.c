#include "netrunner_handoff.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static unsigned checks;
#define CHECK(c) do { checks++; if (!(c)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); exit(1); } } while (0)

static const struct nr_config config = {true, NR_AP, 5000, 2000, 2000, 1500};
static struct nr_policy fresh(void) {
    struct nr_policy p;
    CHECK(nr_init(&p, &config, 42, 0, NR_REQUIRED_GATES));
    return p;
}
static struct nr_action tick(struct nr_policy *p, uint64_t now, enum nr_host host) {
    return nr_tick(p, now, host, now, NR_REQUIRED_GATES);
}
static struct nr_action switch_request(struct nr_policy *p) {
    struct nr_action action;
    for (uint64_t now = 0; now < 5000; now += 1000)
        CHECK(tick(p, now, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    action = tick(p, 5000, NR_HOST_ABSENT);
    CHECK(action.kind == NR_REQUEST_WIFI);
    CHECK(action.request == 1 && action.generation == 42);
    return action;
}

static void validation(void) {
    struct nr_policy p;
    struct nr_config c = config;
    CHECK(!nr_init(NULL, &c, 1, 0, NR_REQUIRED_GATES));
    CHECK(!nr_init(&p, NULL, 1, 0, NR_REQUIRED_GATES));
    CHECK(!nr_init(&p, &c, 0, 0, NR_REQUIRED_GATES));
    c.usb_timeout_ms = 0;
    CHECK(!nr_init(&p, &c, 1, 0, NR_REQUIRED_GATES));
    c = config; c.usb_timeout_ms = 600001;
    CHECK(!nr_init(&p, &c, 1, 0, NR_REQUIRED_GATES));
    c = config; c.mode = (enum nr_mode)0;
    CHECK(!nr_init(&p, &c, 1, 0, NR_REQUIRED_GATES));
    c = config; c.handoff_timeout_ms = UINT32_MAX;
    CHECK(!nr_init(&p, &c, 1, 0, NR_REQUIRED_GATES));
    c = config; c.restore_timeout_ms = 0;
    CHECK(!nr_init(&p, &c, 1, 0, NR_REQUIRED_GATES));
    c = config; c.max_sample_age_ms = 5001;
    CHECK(!nr_init(&p, &c, 1, 0, NR_REQUIRED_GATES));
    c = config; c.enabled = false;
    CHECK(nr_init(&p, &c, 1, 0, NR_REQUIRED_GATES));
    CHECK(tick(&p, 999999, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    CHECK(p.state == NR_DISABLED);
}

static void host_priority_and_absence(void) {
    struct nr_policy p = fresh();
    for (uint64_t now = 0; now <= 30000; now += 1000) {
        CHECK(tick(&p, now, NR_HOST_CONNECTED).kind == NR_NO_ACTION);
        CHECK(p.state == NR_USB_HELD);
    }
    for (uint64_t now = 31000; now < 36000; now += 1000)
        CHECK(tick(&p, now, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    /* A host arriving exactly at expiry wins over automatic Wi-Fi. */
    CHECK(tick(&p, 36000, NR_HOST_CONNECTED).kind == NR_NO_ACTION);
    CHECK(p.state == NR_USB_HELD);
    for (uint64_t now = 37000; now < 42000; now += 1000)
        CHECK(tick(&p, now, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    CHECK(tick(&p, 42000, NR_HOST_ABSENT).kind == NR_REQUEST_WIFI);
}

static void unavailable_or_stale_never_cuts_usb(void) {
    for (uint32_t missing = 1; missing < 128; missing <<= 1) {
        struct nr_policy p = fresh();
        for (uint64_t now = 0; now < 10000; now += 1000)
            CHECK(nr_tick(&p, now, NR_HOST_ABSENT, now,
                         NR_REQUIRED_GATES & ~missing).kind == NR_NO_ACTION);
        CHECK(p.state == NR_WAIT_USB);
    }
    struct nr_policy p = fresh();
    for (uint64_t now = 0; now < 5000; now += 1000)
        CHECK(tick(&p, now, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    CHECK(tick(&p, 5000, NR_HOST_UNKNOWN).kind == NR_NO_ACTION);
    CHECK(tick(&p, 6000, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    CHECK(nr_tick(&p, 7000, NR_HOST_ABSENT, 8000, NR_REQUIRED_GATES).kind == NR_NO_ACTION);
    CHECK(nr_tick(&p, 9000, NR_HOST_ABSENT, 7000, NR_REQUIRED_GATES).kind == NR_NO_ACTION);
    CHECK(tick(&p, 10000, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    /* A suspended process cannot infer continuous absence from two samples. */
    CHECK(tick(&p, 60000, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    CHECK(p.absent_since_ms == 60000);
}

static void correlated_completion_and_recovery(void) {
    struct nr_policy p = fresh();
    struct nr_action action = switch_request(&p);
    CHECK(!nr_complete(&p, 5100, 41, action.request, NR_VERIFIED_WIFI));
    CHECK(!nr_complete(&p, 5100, 42, 999, NR_VERIFIED_WIFI));
    CHECK(!nr_complete(&p, 5100, 42, action.request, NR_VERIFIED_USB));
    CHECK(p.state == NR_SWITCH_PENDING);
    CHECK(nr_complete(&p, 5100, 42, action.request, NR_VERIFIED_WIFI));
    CHECK(p.state == NR_WIFI_VERIFIED);
    /* Once the mux is switched, its apparent missing USB host cannot rearm. */
    CHECK(tick(&p, 90000, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    CHECK(p.state == NR_WIFI_VERIFIED);
    action = nr_return_usb(&p, 91000);
    CHECK(action.kind == NR_REQUEST_USB && action.request == 2);
    CHECK(nr_return_usb(&p, 91001).kind == NR_NO_ACTION);
    CHECK(!nr_complete(&p, 91100, 42, 1, NR_VERIFIED_WIFI));
    CHECK(nr_complete(&p, 91100, 42, action.request, NR_VERIFIED_USB));
    CHECK(p.state == NR_USB_RECOVERED);
    CHECK(tick(&p, 999999, NR_HOST_ABSENT).kind == NR_NO_ACTION);
}

static void deadlines_and_failures(void) {
    struct nr_policy p = fresh();
    struct nr_action action = switch_request(&p);
    CHECK(!nr_complete(&p, 7000, 42, action.request, NR_VERIFIED_WIFI));
    action = tick(&p, 7000, NR_HOST_UNKNOWN);
    CHECK(action.kind == NR_REQUEST_USB);
    CHECK(tick(&p, 7001, NR_HOST_UNKNOWN).kind == NR_NO_ACTION);
    CHECK(tick(&p, 9000, NR_HOST_UNKNOWN).kind == NR_NO_ACTION);
    CHECK(p.state == NR_RECOVERY_REQUIRED);
    CHECK(!nr_complete(&p, 9001, 42, action.request, NR_VERIFIED_USB));
    CHECK(tick(&p, 999999, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    p = fresh(); action = switch_request(&p);
    CHECK(nr_complete(&p, 5100, 42, action.request, NR_FAILED));
    CHECK(tick(&p, 5100, NR_HOST_UNKNOWN).kind == NR_REQUEST_USB);
    CHECK(nr_complete(&p, 5200, 42, 2, NR_FAILED));
    CHECK(p.state == NR_RECOVERY_REQUIRED);
    p = fresh(); action = switch_request(&p);
    CHECK(nr_complete(&p, 5100, 42, 1, NR_VERIFIED_WIFI));
    CHECK(nr_tick(&p, 5200, NR_HOST_UNKNOWN, 5200,
                  NR_REQUIRED_GATES & ~NR_INDEPENDENT_RECOVERY_ARMED).kind == NR_REQUEST_USB);
    CHECK(p.state == NR_RESTORE_PENDING);
}

static void clocks_and_client_mode(void) {
    struct nr_policy p = fresh();
    CHECK(tick(&p, 1000, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    CHECK(tick(&p, 500, NR_HOST_ABSENT).kind == NR_NO_ACTION);
    CHECK(p.state == NR_DISABLED);
    p = fresh(); (void)switch_request(&p);
    CHECK(tick(&p, 4000, NR_HOST_UNKNOWN).kind == NR_REQUEST_USB);
    CHECK(p.state == NR_RESTORE_PENDING);
    struct nr_config c = config; c.mode = NR_CLIENT;
    CHECK(nr_init(&p, &c, 42, 0, NR_REQUIRED_GATES));
    CHECK(switch_request(&p).mode == NR_CLIENT);
}

int main(void) {
    validation(); host_priority_and_absence(); unavailable_or_stale_never_cuts_usb();
    correlated_completion_and_recovery(); deadlines_and_failures(); clocks_and_client_mode();
    printf("Netrunner USB handoff policy: %u checks passed; no hardware executor\n", checks);
    return 0;
}
