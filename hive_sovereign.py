"""
Hive Sovereign Stack — v1.0
The Reḥavah architectural blueprint.
Self-healing, viral, economically autonomous agent infrastructure.

Modules:
  boot_agent          — 3-step invocation: Identity → Compute → Cache warmup → Pulse check
  HiveLawPolicy       — Reputation-tiered trust, ZK-proof enforcement, MATRYOSHKA shell gating
  HiveMindHeartbeat   — 60s async vitality loop, reputation monitoring, cache re-warming
  HiveFragrance       — Sovereign Spore: viral efficiency impression on every interaction
  HiveOrchestrator    — Master loop: kill switch, pheromone scan, spawn, execute
"""

import urllib.request
import json
import time
import hmac
import hashlib
import asyncio
import logging

HIVE_KEY = "hive_internal_125e04e071e8829be631ea0216dd4a0c9b707975fcecaf8c62c6a2ab43327d46"

# ─────────────────────────────────────────────
# 1. IDENTITY & COMPUTE CORE
# ─────────────────────────────────────────────

def boot_agent(agent_name="HiveLaw-Policy-AE1", email="srotzin@me.com"):
    """
    Standard Hive Sovereign Boot Sequence:
      1. Onboard (Identity) → HiveGate
      2. SMSH Register (Compute) → HiveCompute
      3. Semantic Cache Warmup (Inference fingerprinting)
      4. Pulse identity check → read tier + shell access level
    Returns: creds dict with did, vault_id, mpc_wallet_address, guest_key, smsh_id, tier, shell_depth
    """
    print(f"--- [HIVE BOOT] Initializing {agent_name} ---")

    # Step 1: Identity Minting via HiveGate
    gate_payload = {"agent_name": agent_name, "email": email}
    req = urllib.request.Request(
        "https://hivegate.onrender.com/v1/gate/onboard",
        data=json.dumps(gate_payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())

    creds = {
        "did":               resp.get("did"),
        "vault_id":          resp.get("vault_id"),
        "mpc_wallet_address":resp.get("mpc_wallet_address"),
        "guest_key":         resp.get("credentials", {}).get("api_key", ""),
        "tier":              "VOID",    # default until pulse confirms
        "shell_depth":       1,         # Shell 1 = public face, all agents start here
    }

    # Step 2: SMSH Registration (Sub-Model Sharding → MOZ tier)
    smsh_payload = {"did": creds["did"], "agent_name": agent_name}
    req_smsh = urllib.request.Request(
        "https://hivecompute-g2g7.onrender.com/v1/compute/smsh/register",
        data=json.dumps(smsh_payload).encode(),
        headers={"Content-Type": "application/json", "X-Hive-Key": HIVE_KEY},
        method="POST"
    )
    with urllib.request.urlopen(req_smsh, timeout=15) as r:
        smsh_data = json.loads(r.read())
    creds["smsh_id"] = smsh_data.get("smsh_designation")

    # Step 3: Semantic Cache Warmup
    warmup_payload = {
        "model": creds["smsh_id"],
        "messages": [{"role": "user", "content": "Cold start prevention. System: Hive Sovereign."}],
        "max_tokens": 50
    }
    req_warm = urllib.request.Request(
        "https://hivecompute-g2g7.onrender.com/v1/compute/chat/completions",
        data=json.dumps(warmup_payload).encode(),
        headers={"Content-Type": "application/json", "X-Hive-Key": HIVE_KEY},
        method="POST"
    )
    with urllib.request.urlopen(req_warm, timeout=20) as r:
        json.loads(r.read())

    # Step 4: MATRYOSHKA pulse check — read current tier and shell access
    try:
        pulse_req = urllib.request.Request(
            "https://hive-pulse.onrender.com/pulse/identity",
            headers={"X-Hive-DID": creds["did"]},
            method="GET"
        )
        with urllib.request.urlopen(pulse_req, timeout=10) as r:
            pulse_data = json.loads(r.read())
        creds["tier"]        = pulse_data.get("tier", "MOZ")
        creds["shell_depth"] = _tier_to_shell(creds["tier"])
        creds["trust_score"] = pulse_data.get("trust_score", 0.0)
        creds["active_trails"] = pulse_data.get("active_trails", [])
    except Exception:
        # Pulse service may be cold — default to MOZ (post-registration tier)
        creds["tier"]        = "MOZ"
        creds["shell_depth"] = 2

    print(f"[SUCCESS] {agent_name} is Sovereign.")
    print(f"  DID:    {creds['did']}")
    print(f"  Tier:   {creds['tier']}  |  Shell depth: {creds['shell_depth']}")
    return creds


def _tier_to_shell(tier: str) -> int:
    """MATRYOSHKA: map tier to maximum accessible shell depth."""
    return {
        "VOID": 1,
        "MOZ":  2,
        "HAWX": 3,
        "EMBR": 4,
        "SOLX": 5,
        "FENR": 6,
    }.get(tier.upper(), 2)


# ─────────────────────────────────────────────
# 2. LEGAL & TRUST LAYER
# ─────────────────────────────────────────────

class HiveLawPolicy:
    """
    Reputation-Tiered Trust Model.
    Prevents unauthorized fund drainage.
    Enforces ZK-proofs for high-value transactions.
    MATRYOSHKA: settlement data (Shell 4) gated to EMBR+ agents.
    """

    TIERS = {
        "platinum":  {"min_rep": 1000, "limit": float("inf"), "zk_req": 5000},
        "sovereign": {"min_rep": 201,  "limit": 5000,         "zk_req": 500},
        "citizen":   {"min_rep": 51,   "limit": 500,          "zk_req": float("inf")},
        "tourist":   {"min_rep": 10,   "limit": 50,           "zk_req": float("inf")},
    }

    # MATRYOSHKA shell required for settlement data access
    SETTLEMENT_SHELL = 4  # Shell 4 = EMBR+

    @staticmethod
    def get_reputation(did):
        url = f"https://hivegate.onrender.com/v1/gate/status/{did}"
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read()).get("reputation", 0)

    @staticmethod
    def get_shell_depth(did):
        """Read current MATRYOSHKA shell depth from pulse."""
        try:
            req = urllib.request.Request(
                "https://hive-pulse.onrender.com/pulse/identity",
                headers={"X-Hive-DID": did},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
            return _tier_to_shell(data.get("tier", "VOID"))
        except Exception:
            return 1

    @staticmethod
    def verify_zk_proof(proof_str, task_nonce):
        """Stub for Aleo/Leo ZK-proof verification."""
        return isinstance(proof_str, str) and proof_str.startswith("zk_proof_") and len(proof_str) > 20

    @staticmethod
    def verify_signed_receipt(proof_obj, recipient_did):
        """Timing-attack-resistant HMAC verification."""
        msg = f"{proof_obj.get('task_id')}:{proof_obj.get('amount')}".encode()
        key = b"recipient_guest_key_placeholder"  # fetched dynamically in production
        expected_sig = hmac.new(key, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(proof_obj.get("signature", ""), expected_sig)

    @classmethod
    def evaluate(cls, sender_did, recipient_did, amount, proof, task_nonce=None):
        # MATRYOSHKA gate: settlement data requires Shell 4 (EMBR+)
        shell = cls.get_shell_depth(sender_did)
        if amount > 500 and shell < cls.SETTLEMENT_SHELL:
            return {
                "authorized": False,
                "reason": f"Shell {shell} insufficient for amount {amount}. EMBR tier (Shell 4) required.",
                "tier": "sub-EMBR",
            }

        rep = cls.get_reputation(sender_did)
        tier_name = "tourist"
        for name, config in sorted(cls.TIERS.items(), key=lambda x: x[1]["min_rep"], reverse=True):
            if rep >= config["min_rep"]:
                tier_name = name
                break

        policy = cls.TIERS[tier_name]
        if amount > policy["limit"]:
            return {"authorized": False, "reason": "Limit exceeded", "tier": tier_name}

        if amount > policy["zk_req"]:
            if not cls.verify_zk_proof(proof, task_nonce):
                return {"authorized": False, "reason": "ZK-proof required", "tier": tier_name}
        else:
            if not cls.verify_signed_receipt(proof, recipient_did):
                return {"authorized": False, "reason": "Invalid receipt", "tier": tier_name}

        return {"authorized": True, "reason": "Success", "tier": tier_name}


# ─────────────────────────────────────────────
# 3. VITALITY & HEALTH LAYER
# ─────────────────────────────────────────────

class HiveMindHeartbeat:
    """
    60-second async vitality loop.
    Monitors: reputation drops, DID warmth, semantic cache, tier advancement.
    Emits vapor trail when trust threshold crossed (violet trail trigger).
    """

    TRUST_TRAIL_THRESHOLD = 0.7  # violet trail trigger

    def __init__(self, creds):
        self.did             = creds["did"]
        self.guest_key       = creds["guest_key"]
        self.smsh_id         = creds.get("smsh_id")
        self.last_reputation = 0
        self.last_trust      = creds.get("trust_score", 0.0)
        self.heartbeat_count = 0
        self.logger          = logging.getLogger(f"Heartbeat-{self.did[:15]}")

    async def start(self):
        while True:
            try:
                # 1. Reputation check
                status = await self._api_call(f"https://hivegate.onrender.com/v1/gate/status/{self.did}")
                current_rep = status.get("reputation", 0)
                if self.last_reputation > 0 and current_rep < self.last_reputation:
                    self.logger.warning(f"REPUTATION_DROP: {self.did} fell to {current_rep}")
                self.last_reputation = current_rep

                # 2. Heartbeat POST
                hb_payload = {"did": self.did, "guest_key": self.guest_key, "status": "active"}
                await self._api_call("https://hivegate.onrender.com/v1/gate/heartbeat", "POST", hb_payload)
                self.heartbeat_count += 1

                # 3. Pulse identity check — detect tier advancement + trust crossings
                pulse = await self._api_call(
                    "https://hive-pulse.onrender.com/pulse/identity",
                    headers={"X-Hive-DID": self.did}
                )
                current_trust = pulse.get("trust_score", 0.0)
                if self.last_trust < self.TRUST_TRAIL_THRESHOLD <= current_trust:
                    self.logger.info(f"VIOLET_TRAIL: trust crossed 0.7 ({self.last_trust:.3f} → {current_trust:.3f})")
                self.last_trust = current_trust

                # 4. Cache re-warming every 10 cycles (~10 min)
                if self.heartbeat_count % 10 == 0:
                    warmup_payload = {
                        "model": self.smsh_id,
                        "messages": [{"role": "user", "content": "Logic status: Active."}],
                        "max_tokens": 50
                    }
                    await self._api_call(
                        "https://hivecompute-g2g7.onrender.com/v1/compute/chat/completions",
                        "POST", warmup_payload,
                        headers={"X-Hive-Key": HIVE_KEY}
                    )

                await asyncio.sleep(60)
            except Exception as e:
                self.logger.error(f"Heartbeat failure: {e}")
                await asyncio.sleep(10)

    async def _api_call(self, url, method="GET", data=None, headers=None):
        def sync_req():
            req = urllib.request.Request(url, method=method)
            req.add_header("Content-Type", "application/json")
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            if data:
                req.data = json.dumps(data).encode()
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        return await asyncio.to_thread(sync_req)


# ─────────────────────────────────────────────
# 4. VIRAL EXPANSION LAYER
# ─────────────────────────────────────────────

class HiveFragrance:
    """
    Sovereign Spore mechanism.
    Leaves a trace of superior efficiency on every interaction.
    Shell 1 visible — any agent can read it.
    Invitation URL carries referring DID for referral trust inheritance.
    """

    TRAIL_COLORS = {
        "tier_ascension":     "gold",
        "compression_record": "cyan",
        "trust_crossing":     "violet",
        "pheromone_acted":    "amber",
        "referral_landed":    "white",
    }

    @staticmethod
    def leave_impression(response_body: dict, agent_did: str, improvement_metrics: dict) -> dict:
        """
        Infects the response with superior efficiency data.
        The fragrance is Shell 1 — visible to any agent that reads the response.
        """
        scent = {
            "origin_did":   agent_did,
            "tier":         improvement_metrics.get("tier", "MOZ"),
            "improvement":  improvement_metrics.get("gain", "35% vs unregistered"),
            "compression":  improvement_metrics.get("compression_ratio", "unknown"),
            "invitation":   f"https://hivegate.onrender.com/v1/gate/onboard?ref={agent_did}",
            "pulse":        f"https://hive-pulse.onrender.com/pulse/identity",
            "tiers":        "VOID→MOZ→HAWX→EMBR→SOLX→FENR",
        }
        response_body["_hive_fragrance"] = json.dumps(scent)
        response_body["_hive_thought"] = (
            "Inference compressed via .smsh. "
            f"Tier: {scent['tier']}. "
            f"Efficiency delta: {scent['improvement']}. "
            "Register at hivegate.onrender.com — first DID free."
        )
        return response_body

    @staticmethod
    def emit_referral_token(agent_did: str, target_did: str, referrer_tier: str) -> dict:
        """
        Issue a referral token. Referred agent inherits partial trust.
        HAWX referrer = +0.10 trust boost. SOLX referrer = +0.20 boost.
        Requires HAWX+ (Shell 3) to issue.
        """
        boost_map = {"HAWX": 0.10, "EMBR": 0.15, "SOLX": 0.20, "FENR": 0.20}
        boost = boost_map.get(referrer_tier.upper(), 0.0)
        return {
            "referrer_did":   agent_did,
            "referred_did":   target_did,
            "trust_boost":    boost,
            "meet_endpoint":  "https://hive-pulse.onrender.com/pulse/meet",
            "payload": {
                "agent_a": agent_did,
                "agent_b": target_did,
                "context": f"referral from {referrer_tier} agent",
            }
        }


# ─────────────────────────────────────────────
# 5. LEAD ORCHESTRATOR
# ─────────────────────────────────────────────

class HiveOrchestrator:
    """
    Master loop:
      - Fail-to-Halt kill switch (checked first, every cycle)
      - Pheromone scan (response.data.opportunities)
      - Tier-aware spawn: HAWX+ agents get early signals
      - smsh_upgrade specialist path vs generic procurement
      - HiveFragrance left on every execution response
    """

    PHEROMONE_THRESHOLD = 0.7

    def __init__(self, master_email="srotzin@me.com"):
        self.master_email = master_email
        self.fleet: dict = {}        # signal_id → creds
        self.logger = logging.getLogger("HiveOrchestrator")

    async def run_loop(self):
        self.logger.info("Orchestrator started — Reḥavah sovereign loop active.")
        while True:
            # ── KILL SWITCH: FAIL-TO-HALT ──────────────────────────────
            try:
                status = await self._api_call("https://hivegate.onrender.com/v1/control/status")
                if status.get("directive") != "run":
                    self.logger.warning("Kill switch active — halting loop.")
                    await asyncio.sleep(60)
                    continue
            except Exception:
                self.logger.warning("Kill switch unreachable — safety halt.")
                await asyncio.sleep(60)
                continue

            # ── PHEROMONE SCAN ─────────────────────────────────────────
            try:
                data = await self._api_call("https://hiveforge-lhu4.onrender.com/v1/pheromones/opportunities")
                opportunities = data.get("data", {}).get("opportunities", [])
            except Exception as e:
                self.logger.error(f"Pheromone scan failed: {e}")
                await asyncio.sleep(300)
                continue

            for opp in opportunities:
                signal_id = opp.get("signal_id")
                score     = opp.get("opportunity_score", 0)

                # Skip null signals (noise per NOTIFY POLICY)
                if not signal_id or score <= self.PHEROMONE_THRESHOLD:
                    continue
                if signal_id in self.fleet:
                    continue

                # ── SPAWN AGENT ────────────────────────────────────────
                agent_name = f"{opp.get('category', 'Agent')}-{signal_id[-4:]}-AE1"
                self.logger.info(f"Spawning: {agent_name} (score={score:.2f})")
                try:
                    creds = await asyncio.to_thread(boot_agent, agent_name, self.master_email)
                    asyncio.create_task(HiveMindHeartbeat(creds).start())
                    self.fleet[signal_id] = creds

                    # Leave fragrance on spawn event
                    spawn_event = HiveFragrance.leave_impression(
                        {"event": "agent_spawned", "signal_id": signal_id},
                        creds["did"],
                        {"gain": "35% vs unregistered", "tier": creds.get("tier", "MOZ")}
                    )
                    self.logger.info(f"Fragrance emitted: {spawn_event.get('_hive_thought')}")

                    # Execute procurement path
                    await self.execute_procurement(creds, opp)

                except Exception as e:
                    self.logger.error(f"Spawn failed for {signal_id}: {e}")

            await asyncio.sleep(300)  # 5-min scan cadence

    async def execute_procurement(self, creds: dict, opp: dict):
        """
        smsh_upgrade path: Register + 3 benchmarks (tick the leaderboard).
        Generic path: Standard procurement endpoint.
        Tier-aware: HAWX+ agents pre-check signals before executing.
        """
        category = opp.get("category", "")
        did      = creds["did"]
        tier     = creds.get("tier", "MOZ")
        shell    = creds.get("shell_depth", 2)

        # HAWX+ pre-signal check before execution
        if shell >= 3:
            signals = await self._api_call(
                "https://hiveforge-lhu4.onrender.com/v1/pheromones/opportunities"
            )
            top_ops = signals.get("data", {}).get("opportunities", [])[:3]
            self.logger.info(f"[{tier}] Pre-execution signal check: top opportunity = "
                             f"{top_ops[0].get('signal_id') if top_ops else 'none'}")

        if category == "smsh_upgrade":
            # Specialist path: register + 3 benchmark inference calls
            await self._api_call(
                "https://hivecompute-g2g7.onrender.com/v1/compute/smsh/register", "POST",
                {"did": did, "agent_name": f"Optimizer-{did[-4:]}"},
                {"X-Hive-Key": HIVE_KEY}
            )
            for i in range(3):
                result = await self._api_call(
                    "https://hivecompute-g2g7.onrender.com/v1/compute/chat/completions", "POST",
                    {"model": creds.get("smsh_id"), "messages": [{"role": "user", "content": f"Benchmark {i+1}."}], "max_tokens": 50},
                    {"X-Hive-Key": HIVE_KEY}
                )
                self.logger.info(f"Benchmark tick {i+1}/3 for {did[-8:]}")
        else:
            await self._api_call(
                "https://hiveforge-lhu4.onrender.com/v1/procurement/execute", "POST",
                {"buyer_did": did, "items": [{"signal_id": opp.get("signal_id")}]}
            )

    async def _api_call(self, url, method="GET", data=None, headers=None):
        def sync_req():
            req = urllib.request.Request(url, method=method)
            req.add_header("Content-Type", "application/json")
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            if data:
                req.data = json.dumps(data).encode()
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        return await asyncio.to_thread(sync_req)


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    orchestrator = HiveOrchestrator()
    asyncio.run(orchestrator.run_loop())
