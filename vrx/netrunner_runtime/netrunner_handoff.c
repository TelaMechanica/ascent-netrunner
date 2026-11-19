#include "netrunner_handoff.h"
#include <stddef.h>
#include <string.h>

static struct nr_action none(void) {
    const struct nr_action action = {NR_NO_ACTION, NR_AP, 0, 0};
    return action;
}

static bool valid(const struct nr_config *c) {
    return c && (c->mode == NR_AP || c->mode == NR_CLIENT) &&
        c->usb_timeout_ms >= 5000 && c->usb_timeout_ms <= 600000 &&
        c->handoff_timeout_ms >= 1000 && c->handoff_timeout_ms <= 120000 &&
        c->restore_timeout_ms >= 1000 && c->restore_timeout_ms <= 120000 &&
        c->max_sample_age_ms > 0 && c->max_sample_age_ms <= 5000;
}

bool nr_init(struct nr_policy *p, const struct nr_config *c, uint64_t generation,
             uint64_t now_ms, uint32_t gates) {
    if (!p) return false;
    memset(p, 0, sizeof(*p));
    p->state = NR_DISABLED;
    if (!valid(c) || generation == 0) return false;
    p->config = *c;
    p->generation = generation;
    p->last_ms = now_ms;
    p->gates = gates;
    if (c->enabled) p->state = NR_WAIT_USB;
    return true;
}

static struct nr_action request_usb(struct nr_policy *p, uint64_t now_ms) {
    p->state = NR_RESTORE_PENDING;
    p->pending_since_ms = now_ms;
    p->request++;
    const struct nr_action action = {NR_REQUEST_USB, p->config.mode,
                                      p->generation, p->request};
    return action;
}

struct nr_action nr_return_usb(struct nr_policy *p, uint64_t now_ms) {
    if (!p) return none();
    if (now_ms < p->last_ms) now_ms = p->last_ms;
    p->last_ms = now_ms;
    if (p->state == NR_SWITCH_PENDING || p->state == NR_SWITCH_FAILED || p->state == NR_WIFI_VERIFIED)
        return request_usb(p, now_ms);
    return none();
}

struct nr_action nr_tick(struct nr_policy *p, uint64_t now_ms,
                         enum nr_host host, uint64_t sample_ms, uint32_t gates) {
    if (!p) return none();
    /* Clock regression before a handoff forbids it; after a handoff request,
     * request USB restoration once rather than extending an unknown deadline. */
    if (now_ms < p->last_ms) {
        if (p->state == NR_SWITCH_PENDING || p->state == NR_SWITCH_FAILED || p->state == NR_WIFI_VERIFIED)
            return nr_return_usb(p, p->last_ms);
        if (p->state != NR_RESTORE_PENDING) p->state = NR_DISABLED;
        return none();
    }
    p->last_ms = now_ms;
    p->gates = gates;
    if (p->state == NR_SWITCH_FAILED) return request_usb(p, now_ms);
    if (p->state == NR_RESTORE_PENDING) {
        if (now_ms - p->pending_since_ms >= p->config.restore_timeout_ms)
            p->state = NR_RECOVERY_REQUIRED;
        return none();
    }
    if (p->state == NR_SWITCH_PENDING || p->state == NR_WIFI_VERIFIED) {
        if ((gates & NR_REQUIRED_GATES) != NR_REQUIRED_GATES ||
            (p->state == NR_SWITCH_PENDING &&
             now_ms - p->pending_since_ms >= p->config.handoff_timeout_ms))
            return request_usb(p, now_ms);
        return none();
    }
    if (p->state != NR_WAIT_USB && p->state != NR_USB_HELD) return none();
    if ((gates & NR_REQUIRED_GATES) != NR_REQUIRED_GATES ||
        sample_ms > now_ms || now_ms - sample_ms > p->config.max_sample_age_ms ||
        (host != NR_HOST_ABSENT && host != NR_HOST_CONNECTED)) {
        p->state = NR_WAIT_USB;
        p->absent_timing = false;
        p->have_usb_sample = false;
        return none();
    }
    if (p->have_usb_sample &&
        sample_ms - p->last_usb_sample_ms > p->config.max_sample_age_ms)
        p->absent_timing = false;
    p->last_usb_sample_ms = sample_ms;
    p->have_usb_sample = true;
    if (host == NR_HOST_CONNECTED) {
        p->state = NR_USB_HELD;
        p->absent_timing = false;
        return none();
    }
    p->state = NR_WAIT_USB;
    if (!p->absent_timing) {
        p->absent_since_ms = now_ms;
        p->absent_timing = true;
    }
    if (now_ms - p->absent_since_ms < p->config.usb_timeout_ms) return none();
    p->state = NR_SWITCH_PENDING;
    p->pending_since_ms = now_ms;
    p->request++;
    const struct nr_action action = {NR_REQUEST_WIFI, p->config.mode,
                                      p->generation, p->request};
    return action;
}

bool nr_complete(struct nr_policy *p, uint64_t now_ms, uint64_t generation,
                 uint32_t request, enum nr_result result) {
    if (!p || now_ms < p->last_ms || generation != p->generation ||
        request != p->request) return false;
    if (p->state == NR_SWITCH_PENDING) {
        if (result != NR_VERIFIED_WIFI && result != NR_FAILED) return false;
        /* A late success cannot cancel a recovery deadline. tick emits the
         * restore request; callers must process it even if a tool reports OK. */
        if (now_ms - p->pending_since_ms >= p->config.handoff_timeout_ms)
            return false;
        p->last_ms = now_ms;
        if (result == NR_VERIFIED_WIFI) p->state = NR_WIFI_VERIFIED;
        else p->state = NR_SWITCH_FAILED;
        return true;
    }
    if (p->state == NR_RESTORE_PENDING) {
        if (result != NR_VERIFIED_USB && result != NR_FAILED) return false;
        if (now_ms - p->pending_since_ms >= p->config.restore_timeout_ms)
            return false;
        p->last_ms = now_ms;
        p->state = result == NR_VERIFIED_USB ? NR_USB_RECOVERED : NR_RECOVERY_REQUIRED;
        return true;
    }
    return false;
}
