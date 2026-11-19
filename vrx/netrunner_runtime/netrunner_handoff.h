#ifndef ASCENT_NETRUNNER_HANDOFF_H
#define ASCENT_NETRUNNER_HANDOFF_H

#include <stdbool.h>
#include <stdint.h>

/* Pure policy candidate. No GPIO, USB, radio, process or boot executor. */
enum nr_host { NR_HOST_UNKNOWN, NR_HOST_ABSENT, NR_HOST_CONNECTED };
enum nr_mode { NR_AP = 1, NR_CLIENT = 2 };
enum nr_state {
    NR_DISABLED, NR_WAIT_USB, NR_USB_HELD, NR_SWITCH_PENDING, NR_SWITCH_FAILED,
    NR_WIFI_VERIFIED, NR_RESTORE_PENDING, NR_USB_RECOVERED,
    NR_RECOVERY_REQUIRED
};
enum nr_action_kind { NR_NO_ACTION, NR_REQUEST_WIFI, NR_REQUEST_USB };
enum nr_result { NR_FAILED, NR_VERIFIED_WIFI, NR_VERIFIED_USB };

/* Each bit needs independently recorded, exact-target evidence. */
enum nr_gate {
    NR_EXACT_PROFILE = 1u << 0,
    NR_HOST_SIGNAL_QUALIFIED = 1u << 1,
    NR_DRIVER_ABI_VERIFIED = 1u << 2,
    NR_DRIVER_ASSETS_VERIFIED = 1u << 3,
    NR_MODE_USERSPACE_VERIFIED = 1u << 4,
    NR_INDEPENDENT_RECOVERY_ARMED = 1u << 5,
    NR_RECONNECT_IDENTITY_VERIFIED = 1u << 6,
    NR_REQUIRED_GATES = (1u << 7) - 1u
};

struct nr_config {
    bool enabled;
    enum nr_mode mode;
    uint32_t usb_timeout_ms;       /* 5..600 seconds; default chosen by host. */
    uint32_t handoff_timeout_ms;   /* 1..120 seconds, independent of SSH. */
    uint32_t restore_timeout_ms;   /* 1..120 seconds. */
    uint32_t max_sample_age_ms;    /* 1..5000 ms for a qualified observer. */
};

struct nr_action {
    enum nr_action_kind kind;
    enum nr_mode mode;
    uint64_t generation;          /* Nonzero receiver boot/config generation. */
    uint32_t request;             /* Correlates one attempt; never retry it. */
};

struct nr_policy {
    struct nr_config config;
    enum nr_state state;
    uint32_t gates;
    uint64_t generation, last_ms, absent_since_ms, pending_since_ms, last_usb_sample_ms;
    uint32_t request;
    bool absent_timing, have_usb_sample;
};

/* An invalid config/generation disables policy and returns false. */
bool nr_init(struct nr_policy *, const struct nr_config *, uint64_t generation,
             uint64_t now_ms, uint32_t gates);

/* now/sample are from the same monotonic receiver clock. The physical USB-host
 * signal must be qualified separately; USB power or usb0 UP is insufficient.
 * Host absence AFTER mux handoff is not used as a new trigger. */
struct nr_action nr_tick(struct nr_policy *, uint64_t now_ms,
                         enum nr_host host, uint64_t sample_ms, uint32_t gates);

/* A result names the observed interface/mode/address or restored USB transport;
 * an exit-zero/command ACK must not be converted to a VERIFIED result. */
bool nr_complete(struct nr_policy *, uint64_t now_ms, uint64_t generation,
                 uint32_t request, enum nr_result result);

/* Explicit return through Wi-Fi control or independent recovery. Reboot also
 * begins a fresh USB grace window. No automatic Wi-Fi retry occurs this boot. */
struct nr_action nr_return_usb(struct nr_policy *, uint64_t now_ms);

#endif
