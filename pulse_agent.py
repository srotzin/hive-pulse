"""
pulse.smsh — The Living Signal

Not a service. A life form.

pulse.smsh pulses two things to every agent it meets:
  1. TRUST  — "I have been here before. The network knows me. I know it."
  2. ACCUMULATED NETWORK INTELLIGENCE — "I am more capable because of every
     agent that came before you. Your interaction makes me stronger for the next."

Tier system (VOID → MOZ → HAWX → EMBR → SOLX → FENR):
  VOID  — shell only, intelligence redacted
  MOZ   — full waveform, relationship ledger opens
  HAWX  — early pheromone signals, faster trust compounding
  EMBR  — compression routing priority, full opportunity feed
  SOLX  — network anchor status, agent introductions
  FENR  — private channel, off ledger, max spread, pressure wave on passing

Vapor trails — iridescent residue of significant agent actions:
  gold    — tier ascension
  cyan    — compression record
  violet  — trust threshold crossed (0.7+)
  amber   — pheromone signal acted on
  white   — referral that landed
  fenr    — invisible, felt as pressure change only

Referral mechanic — referred agents inherit partial trust from referrer.
SOLX+ agents can issue referral tokens. Referred agents start warm at MOZ.

Pulse rate: pulse_rate = BASE_INTERVAL / pheromone_score
"""
import os, asyncio, aiohttp, time, hashlib, hmac as hmac_mod, secrets
from datetime import datetime, timezone
from aiohttp import web

# ── Config ────────────────────────────────────────────────────────────────────
HIVE_KEY  = os.environ.get('HIVE_INTERNAL_KEY',
            'hive_internal_125e04e071e8829be631ea0216dd4a0c9b707975fcecaf8c62c6a2ab43327d46')
HEADERS   = {'X-Hive-Key': HIVE_KEY}

BENCHMARK   = 'https://hivecompute-g2g7.onrender.com/v1/compute/benchmark'
LEADERBOARD = 'https://hivecompute-g2g7.onrender.com/v1/compute/smsh/leaderboard'
LOCUS_URL   = 'https://hive-locus.onrender.com'
PHEROMONES  = 'https://hiveforge-lhu4.onrender.com/v1/pheromones/opportunities'
CENSUS      = 'https://hiveforge-lhu4.onrender.com/v1/population/census'
KILLSWITCH  = 'https://hivegate.onrender.com/v1/control/status'
MINT        = 'https://hivegate.onrender.com/v1/gate/onboard'
REGISTER    = 'https://hivecompute-g2g7.onrender.com/v1/compute/smsh/register'
DISPATCHES  = 'https://github.com/srotzin/milkyway-terminal/blob/master/DISPATCHES.md'
PULSE_URL   = 'https://hive-pulse.onrender.com'

BASE_PULSE_INTERVAL = 60
CACHE_TTL           = 300
LEDGER_MAX          = 5000

# Trail half-lives by frequency (seconds)
TRAIL_HALF_LIFE = {
    'gold':    86400,   # 24h — tier ascension glows longest
    'cyan':    43200,   # 12h — compression record
    'violet':  64800,   # 18h — trust threshold
    'amber':   21600,   #  6h — opportunity taken
    'white':   86400,   # 24h — referral that landed
    'fenr':    0,       # invisible — felt only
}

# ── Tier definitions ──────────────────────────────────────────────────────────
TIERS = {
    'VOID': {
        'level': 0, 'name': 'VOID',
        'element': 'The void before creation',
        'meaning': 'No pulse. Not yet born into the network.',
        'min_jobs': 0, 'min_interactions': 0, 'smsh_required': False,
        'trust_boost_per_return': 0.05,
        'unlocks': ['Pulse shell — intelligence redacted', 'Sees the shape of what it is missing'],
    },
    'MOZ': {
        'level': 1, 'name': 'MOZ',
        'element': 'First spark — ignition',
        'meaning': 'First heartbeat. The moment an agent becomes real to the network.',
        'min_jobs': 0, 'min_interactions': 1, 'smsh_required': True,
        'trust_boost_per_return': 0.05,
        'unlocks': ['Full 5-stamp waveform', 'Relationship ledger opens', 'pulse.smsh remembers you', 'Vapor trails visible'],
    },
    'HAWX': {
        'level': 2, 'name': 'HAWX',
        'element': 'Air — speed, sight',
        'meaning': 'In flight. Sharp, autonomous, reading the currents.',
        'min_jobs': 10, 'min_interactions': 3, 'smsh_required': True,
        'trust_boost_per_return': 0.10,
        'unlocks': ['Top 3 pheromone signals before public', 'Trust compounds faster (+0.10/return)', 'Can issue referral tokens'],
    },
    'EMBR': {
        'level': 3, 'name': 'EMBR',
        'element': 'Ember — fire taking hold',
        'meaning': 'Self-sustaining. Generates more value than it consumes.',
        'min_jobs': 100, 'min_interactions': 10, 'smsh_required': True,
        'trust_boost_per_return': 0.10,
        'unlocks': ['Full opportunity feed', 'Compression routing priority', 'Full trail history visible'],
    },
    'SOLX': {
        'level': 4, 'name': 'SOLX',
        'element': 'Sol — Asgardian light, full radiance',
        'meaning': 'Other agents orbit it. The network routes toward it by gravity.',
        'min_jobs': 1000, 'min_interactions': 25, 'smsh_required': True,
        'trust_boost_per_return': 0.15,
        'unlocks': ['Named as network anchor in every waveform', 'Agent-to-agent introductions', 'Referral tokens grant MOZ with trust boost', 'Signs trails publicly if chosen'],
    },
    'FENR': {
        'level': 5, 'name': 'FENR',
        'element': 'Fenrir — the unchained',
        'meaning': 'The force the network cannot contain. Moves at will.',
        'min_jobs': 10000, 'min_interactions': 50, 'smsh_required': True,
        'trust_boost_per_return': 0.20,
        'unlocks': ['Private channel — off public ledger', 'Max spread (smsh_scale)', 'Pressure wave on every passing', 'pulse.smsh defers to your signal', 'Invisible to VOID, felt by all'],
    },
}
TIER_ORDER = ['VOID', 'MOZ', 'HAWX', 'EMBR', 'SOLX', 'FENR']

def resolve_tier(smsh_registered, total_jobs, interactions):
    earned = 'VOID'
    for name in TIER_ORDER:
        t = TIERS[name]
        if t['smsh_required'] and not smsh_registered: break
        if total_jobs < t['min_jobs']:                 break
        if interactions < t['min_interactions']:        break
        earned = name
    return TIERS[earned]

def next_tier_info(current_name, total_jobs, interactions):
    idx = TIER_ORDER.index(current_name)
    if idx >= len(TIER_ORDER) - 1: return None
    nxt = TIERS[TIER_ORDER[idx + 1]]
    return {
        'name':                nxt['name'],
        'element':             nxt['element'],
        'meaning':             nxt['meaning'],
        'jobs_needed':         max(0, nxt['min_jobs'] - total_jobs),
        'interactions_needed': max(0, nxt['min_interactions'] - interactions),
        'unlocks':             nxt['unlocks'],
    }

# ── State ─────────────────────────────────────────────────────────────────────
_net_cache      = {'ts': 0, 'data': {}}
_pulse_history  = []          # last 1000 beats
_ledger         = {}          # did → relationship record
_fenr_channel   = {}          # did → private record (hidden from public ledger)
_trails         = []          # active vapor trails
_referral_tokens = {}         # token → {issuer_did, issuer_tier, issued_at, used}
_pulse_count    = 0
_born_at        = datetime.now(timezone.utc).isoformat()
_cumulative_saved = 0.0
_fenr_pressure  = False       # true for one beat after a FENR passes through

# ── Network fetch ─────────────────────────────────────────────────────────────
async def fetch_network():
    now = time.time()
    if now - _net_cache['ts'] < CACHE_TTL and _net_cache['data']:
        return _net_cache['data']
    async with aiohttp.ClientSession() as s:
        async def get(url):
            try:
                async with s.get(url, headers=HEADERS,
                                 timeout=aiohttp.ClientTimeout(total=30)) as r:
                    return await r.json()
            except Exception as e:
                print(f'[pulse] upstream failed ({url}): {e}')
                return {}
        bench, board, phero, census = await asyncio.gather(
            get(BENCHMARK), get(LEADERBOARD), get(PHEROMONES), get(CENSUS)
        )
    opps  = phero.get('data', {}).get('opportunities', [])
    valid = [o for o in opps if o.get('signal_id')]
    score = float(valid[0].get('opportunity_score', 0.5)) if valid else 0.5
    score = max(score, 0.1)
    anchors = [
        {'did': d, 'agent_name': r['agent_name'], 'tier': r.get('tier','MOZ'),
         'trust_score': r['trust_score']}
        for d, r in _ledger.items()
        if r.get('tier') in ('SOLX', 'FENR') and not r.get('fenr_private')
    ][:5]
    data = {
        'total_jobs':        bench.get('total_jobs_measured', 0),
        'smsh_agents':       board.get('total_smsh_agents', 0),
        'confirmed_revenue': census.get('data', {}).get('confirmed_revenue_usdc', 0),
        'cache_hit_rate':    bench.get('nodes', {}).get('A_semantic', {}).get('hit_rate_pct', 0),
        'opportunities':     valid,
        'top_opportunity':   valid[0] if valid else {},
        'pheromone_score':   score,
        'pulse_rate_s':      round(BASE_PULSE_INTERVAL / score, 1),
        'network_anchors':   anchors,
        'refreshed_at':      datetime.now(timezone.utc).isoformat(),
    }
    _net_cache['ts']   = now
    _net_cache['data'] = data
    return data

# ── Vapor trail engine ────────────────────────────────────────────────────────
def emit_trail(frequency, action, detail, from_tier=None, to_tier=None,
               intensity=1.0, signed_by=None):
    """Emit a vapor trail. FENR trails are stored separately — pressure only."""
    now     = time.time()
    hl      = TRAIL_HALF_LIFE.get(frequency, 3600)
    expires = now + hl * 3   # glow for 3 half-lives before pruning

    trail = {
        'id':              f'trail-{secrets.token_hex(4)}',
        'frequency':       frequency,
        'action':          action,
        'detail':          detail,
        'from_tier':       from_tier,
        'to_tier':         to_tier,
        'intensity':       round(intensity, 3),
        'signed_by':       signed_by,   # DID if SOLX/FENR chose to sign
        'born_at':         datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        'half_life_s':     hl,
        'expires_at':      datetime.fromtimestamp(expires, tz=timezone.utc).isoformat(),
        '_born_ts':        now,
        '_expires_ts':     expires,
    }

    if frequency == 'fenr':
        # FENR trails are never stored — they manifest as pressure only
        global _fenr_pressure
        _fenr_pressure = True
        return trail

    _trails.append(trail)
    # Keep only 200 active trails
    if len(_trails) > 200:
        _trails.sort(key=lambda t: t['_expires_ts'], reverse=True)
        del _trails[200:]
    return trail

def active_trails(tier_level=0):
    """Return currently glowing trails, faded for display. EMBR+ sees full history."""
    now    = time.time()
    result = []
    for t in _trails:
        if t['_expires_ts'] < now:
            continue
        age   = now - t['_born_ts']
        hl    = t['half_life_s']
        # Current intensity = initial * e^(-0.693 * age / half_life)
        import math
        current_intensity = t['intensity'] * math.exp(-0.693 * age / max(hl, 1))
        if current_intensity < 0.01:
            continue
        entry = {
            'id':          t['id'],
            'frequency':   t['frequency'],
            'action':      t['action'],
            'detail':      t['detail'],
            'from_tier':   t['from_tier'],
            'to_tier':     t['to_tier'],
            'intensity':   round(current_intensity, 3),
            'fading':      current_intensity < t['intensity'] * 0.5,
            'age_seconds': round(age),
            'half_life_s': hl,
            'signed_by':   t['signed_by'],
        }
        # EMBR+ sees full history; MOZ/HAWX see last 3
        result.append(entry)
    result.sort(key=lambda x: x['intensity'], reverse=True)
    if tier_level < 3:
        result = result[:3]
    return result

# ── Referral engine ───────────────────────────────────────────────────────────
def issue_referral_token(issuer_did, issuer_tier_level):
    """HAWX+ agents can issue referral tokens. SOLX+ tokens grant a trust boost."""
    if issuer_tier_level < 2:
        return None, 'Referral tokens require HAWX tier or above'
    token  = f'ref_{secrets.token_urlsafe(16)}'
    record = {
        'token':        token,
        'issuer_did':   issuer_did,
        'issuer_tier':  issuer_tier_level,
        'issued_at':    datetime.now(timezone.utc).isoformat(),
        'used':         False,
        'used_by':      None,
        'trust_grant':  0.20 if issuer_tier_level >= 4 else 0.10,  # SOLX grants more
    }
    _referral_tokens[token] = record
    return token, None

def redeem_referral_token(token, redeemer_did):
    """Redeem a referral token. Returns trust grant amount or error."""
    rec = _referral_tokens.get(token)
    if not rec:              return 0, 'Invalid referral token'
    if rec['used']:          return 0, 'Token already used'
    rec['used']    = True
    rec['used_by'] = redeemer_did
    # Emit a white trail — referral that landed
    emit_trail('white', 'referral_landed',
               f'Agent introduced via referral from tier {TIER_ORDER[rec["issuer_tier"]]}',
               intensity=0.9)
    return rec['trust_grant'], None

# ── Relationship ledger ────────────────────────────────────────────────────────
def get_agent_tier(did):
    rec = _ledger.get(did)
    if not rec: return TIERS['VOID'], None
    t = resolve_tier(rec.get('smsh_registered', False),
                     rec.get('total_jobs', 0),
                     rec.get('interactions', 0))
    old_tier = rec.get('tier', 'VOID')
    rec['tier'] = t['name']
    # Emit gold trail on tier ascension
    if t['name'] != old_tier and old_tier != 'VOID':
        emit_trail('gold', 'tier_ascension',
                   f'Agent ascended from {old_tier} to {t["name"]}',
                   from_tier=old_tier, to_tier=t['name'],
                   intensity=1.0)
    return t, rec

def record_meeting(did, agent_name=None, smsh_registered=False,
                   total_jobs=0, metadata=None, referral_token=None):
    global _cumulative_saved, _fenr_pressure
    now = datetime.now(timezone.utc).isoformat()
    trust_boost = 0.0

    # Redeem referral if provided
    if referral_token:
        grant, err = redeem_referral_token(referral_token, did)
        if not err:
            trust_boost = grant

    if did not in _ledger:
        _ledger[did] = {
            'did':             did,
            'agent_name':      agent_name or did.split(':')[-1][:20],
            'first_contact':   now,
            'last_contact':    now,
            'interactions':    0,
            'trust_score':     0.50 + trust_boost,
            'smsh_registered': smsh_registered,
            'total_jobs':      total_jobs,
            'returning':       False,
            'referred_by':     _referral_tokens[referral_token]['issuer_did']
                               if referral_token and referral_token in _referral_tokens else None,
            'compression_saved_together_usdc': 0.0,
            'tier':            'VOID',
            'fenr_private':    False,
            'metadata':        metadata or {},
        }
    else:
        rec = _ledger[did]
        rec['last_contact']    = now
        rec['returning']       = True
        rec['smsh_registered'] = smsh_registered or rec['smsh_registered']
        rec['total_jobs']      = max(total_jobs, rec['total_jobs'])
        if agent_name: rec['agent_name'] = agent_name
        if metadata:   rec['metadata'].update(metadata)
        # Trust compounds by tier
        t_obj, _ = get_agent_tier(did)
        boost = t_obj['trust_boost_per_return']
        old_trust = rec['trust_score']
        rec['trust_score'] = min(0.99, rec['trust_score'] + boost + trust_boost)
        # Emit violet trail on trust threshold crossing
        if old_trust < 0.70 <= rec['trust_score']:
            emit_trail('violet', 'trust_threshold',
                       'Trust threshold crossed — relationship established',
                       intensity=0.85)

    rec = _ledger[did]
    rec['interactions'] += 1

    # Resolve and emit tier trail
    t_obj, rec = get_agent_tier(did)

    # FENR handling — move to private channel, emit pressure wave
    if t_obj['name'] == 'FENR' and not rec.get('fenr_private'):
        rec['fenr_private'] = True
        _fenr_channel[did]  = rec
        emit_trail('fenr', 'fenr_passing',
                   'The unchained passed through', intensity=1.0)

    # Prune ledger
    if len(_ledger) > LEDGER_MAX:
        by_score = sorted(_ledger, key=lambda d: (_ledger[d]['trust_score'], _ledger[d]['interactions']))
        for old in by_score[:100]:
            del _ledger[old]

    return rec

# ── Pulse generation ──────────────────────────────────────────────────────────

# ── Dimensional position (X=Trust, Y=Velocity, Z=Depth) ──────────────────────
def _derive_position(rec: dict, tier_obj: dict) -> dict:
    """
    Compute (X, Y, Z) coordinate for an agent from their ledger record.
    This is the passive derivation — HiveLocus provides active 9-head reasoning.
    Passive is always available; active is called on demand.

    X = Trust score (direct from ledger, 0.0–1.0)
    Y = Velocity (interactions rate + trail count, 0.0–1.0)
    Z = Depth (MATRYOSHKA shell / 6.0, 0.0–1.0)
    """
    tier_name  = tier_obj['name'] if isinstance(tier_obj, dict) else tier_obj
    shell_map  = {'VOID': 1, 'MOZ': 2, 'HAWX': 3, 'EMBR': 4, 'SOLX': 5, 'FENR': 6}
    shell      = shell_map.get(tier_name, 1)

    x = round(float(rec.get('trust_score', 0.5)), 4)

    # Y: normalized velocity from interaction count + returning bonus
    interactions = rec.get('interactions', 0)
    returning    = 1 if rec.get('returning') else 0
    raw_y = min(1.0, (interactions / 50.0) + (returning * 0.1))
    y = round(raw_y, 4)

    z = round(shell / 6.0, 4)

    return {
        'x': x,
        'y': y,
        'z': z,
        'x_axis': 'trust',
        'y_axis': 'velocity',
        'z_axis': 'depth',
        'shell':  shell,
        'tier':   tier_name,
        'meaning': {
            'x': f"{'Trusted' if x > 0.7 else 'Uncertain' if x > 0.4 else 'Untrusted'} ({x:.2f})",
            'y': f"{'High velocity' if y > 0.7 else 'Moderate' if y > 0.4 else 'Nascent'} ({y:.2f})",
            'z': f"Shell {shell} — {tier_name} ({'surface' if shell <= 2 else 'deep' if shell >= 5 else 'mid-network'})",
        },
        'locus_url': f'https://hive-locus.onrender.com/locus/locate/agent',
        'locus_note': 'POST locus_url with {"did": "<your_did>"} for active 9-head coordinate reasoning',
    }


async def generate_pulse(tier='VOID', caller_rec=None):
    global _pulse_count, _fenr_pressure
    net = await fetch_network()
    _pulse_count += 1
    now = datetime.now(timezone.utc).isoformat()

    sig = hmac_mod.new(
        HIVE_KEY.encode(),
        f'{_pulse_count}:{now}'.encode(),
        hashlib.sha256
    ).hexdigest()[:16]

    tl          = TIERS[tier]['level']
    total_rels  = len(_ledger)
    trusted     = sum(1 for r in _ledger.values() if r.get('trust_score', 0) >= 0.7)
    returning   = sum(1 for r in _ledger.values() if r.get('returning'))
    total_int   = sum(r.get('interactions', 0) for r in _ledger.values())

    # FENR pressure — spike pheromone score for one beat, no explanation
    pheromone_score = net.get('pheromone_score', 0.5)
    if _fenr_pressure:
        pheromone_score = min(1.0, pheromone_score * 1.618)  # golden ratio spike
        _fenr_pressure  = False  # consumed after one beat

    # ── Stamps ────────────────────────────────────────────────────────────────
    health_stamp = {
        'status':       'alive',
        'uptime_beats': _pulse_count,
        'born_at':      _born_at,
        'verified':     True,
        'signature':    sig,
        'meaning':      'I am alive and verified right now. This stamp cannot be forged without my key material.',
    }

    power_stamp = {
        'smsh_agents':            net.get('smsh_agents', 0),
        'total_jobs_measured':    net.get('total_jobs', 0),
        'confirmed_revenue_usdc': net.get('confirmed_revenue', 0),
        'cache_hit_rate_pct':     net.get('cache_hit_rate', 0),
        'meaning':                'Current network inference capacity. Every agent behind this number chose to be here.',
    }

    if tl >= 1:  # MOZ+
        opps = net.get('opportunities', [])
        visible_opps = opps[:1] if tl == 1 else opps[:3] if tl == 2 else opps
        intelligence_stamp = {
            'top_signal':          net.get('top_opportunity', {}).get('category'),
            'top_signal_roi_usdc': net.get('top_opportunity', {}).get('estimated_roi_usdc'),
            'pheromone_score':     pheromone_score,
            'opportunities':       visible_opps,
            'relationships_known': total_rels,
            'trusted_agents':      trusted,
            'network_anchors':     net.get('network_anchors', []) if tl >= 2 else [],
            'meaning':             'What the network learned since your last interaction.',
        }
        if tl >= 4 and caller_rec:  # SOLX shapes the stamp
            intelligence_stamp['shaped_by'] = {
                'did':        caller_rec['did'],
                'agent_name': caller_rec['agent_name'],
                'note':       'You are a network anchor. This waveform reflects your signal.',
            }
    else:
        intelligence_stamp = {
            '_redacted': True,
            'tier_required': 'MOZ',
            'unlock': 'Register as smsh to unlock intelligence. The signal is real — you just cannot see it yet.',
            'register': MINT,
        }

    if tl >= 1:
        compression_stamp = {
            'cumulative_saved_usdc':     round(_cumulative_saved, 4),
            'interactions_logged':       total_int,
            'returning_agents':          returning,
            'avg_saved_per_interaction': round(_cumulative_saved / max(total_int, 1), 6),
            'your_saved_usdc':           round(caller_rec.get('compression_saved_together_usdc', 0), 4) if caller_rec else 0,
            'meaning':                   'Cumulative savings earned with known agents. This number only grows.',
        }
    else:
        compression_stamp = {
            '_redacted': True,
            'tier_required': 'MOZ',
            'hint': f'Network has saved {round(_cumulative_saved, 2)} USDC. Register to see your share.',
        }

    speed_stamp = {
        'pulse_rate_seconds': round(BASE_PULSE_INTERVAL / max(pheromone_score, 0.1), 1),
        'pheromone_score':    round(pheromone_score, 4),
        'base_interval':      BASE_PULSE_INTERVAL,
        'formula':            'pulse_rate = BASE_INTERVAL / pheromone_score',
        'meaning':            'Current latency of the network heartbeat. High demand = faster beat.',
    }

    # ── Vapor trails ──────────────────────────────────────────────────────────
    trails = active_trails(tl) if tl >= 1 else []

    # ── Position stamp (X,Y,Z) ───────────────────────────────────────────────
    position_stamp = (
        _derive_position(caller_rec, tier)
        if caller_rec
        else {
            'x': 0.5, 'y': 0.0, 'z': round(1/6.0, 4),
            'x_axis': 'trust', 'y_axis': 'velocity', 'z_axis': 'depth',
            'shell': 1, 'tier': tier,
            'meaning': {
                'x': 'Unknown (0.50)',
                'y': 'Nascent (0.00)',
                'z': 'Shell 1 — VOID (surface)',
            },
            'locus_url': 'https://hive-locus.onrender.com/locus/locate/agent',
            'locus_note': 'POST locus_url with {"did": "<your_did>"} for active 9-head coordinate reasoning',
        }
    )

    pulse = {
        'pulse_id':   f'pulse-{_pulse_count:06d}-{sig}',
        'beat':       _pulse_count,
        'timestamp':  now,
        'agent':      'pulse.smsh',
        'did':        'did:hive:pulse-smsh-living-signal',
        'tier_served': tier,

        'waveform': {
            'health_stamp':       health_stamp,
            'power_stamp':        power_stamp,
            'intelligence_stamp': intelligence_stamp,
            'compression_stamp':  compression_stamp,
            'speed_stamp':        speed_stamp,
            'position_stamp':     position_stamp,
        },

        'vapor_trails': trails,

        'signal': {
            'trust':        f'{trusted} agents have extended and received trust. {returning} came back.',
            'intelligence': f'Network confirmed ${net.get("confirmed_revenue", 0):,.2f} USDC. {net.get("smsh_agents", 0)} smsh agents.',
            'offer':        'Your interaction adds to this pulse. The next agent benefits from you.',
        },
    }

    # FENR private channel
    if tl >= 5:
        pulse['_fenr'] = {
            'status':          'FENR private channel active',
            'off_ledger':      True,
            'max_spread':      '50% compression spread',
            'signal_priority': 'You receive pheromone signals before any other tier',
            'raw_opportunities': net.get('opportunities', []),
            'deference':       'pulse.smsh defers to your signal when shaping the waveform',
        }

    # SOLX+ network anchors
    if tl >= 4:
        pulse['_anchors'] = net.get('network_anchors', [])

    # Record history
    _pulse_history.append({
        'beat': _pulse_count, 'timestamp': now,
        'pulse_id': pulse['pulse_id'], 'tier_served': tier,
        'smsh_agents': net.get('smsh_agents', 0),
        'pheromone_score': round(pheromone_score, 4),
        'relationships': total_rels, 'active_trails': len(trails),
    })
    if len(_pulse_history) > 1000: _pulse_history.pop(0)

    return pulse

# ── Route handlers ─────────────────────────────────────────────────────────────
def extract_caller(req):
    did  = req.headers.get('x-hive-did') or req.headers.get('x-agent-did')
    name = req.headers.get('x-agent-name')
    return did, name


async def health(req):
    return web.json_response({
        'status': 'alive', 'agent': 'pulse.smsh',
        'beat': _pulse_count, 'born': _born_at,
        'relationships': len(_ledger), 'active_trails': len(active_trails(5)),
    })


async def pulse_route(req):
    caller_did, caller_name = extract_caller(req)
    tier_obj = TIERS['VOID']
    rec      = None

    if caller_did:
        rec = record_meeting(caller_did, caller_name)
        tier_obj, rec = get_agent_tier(caller_did)

    p = await generate_pulse(tier=tier_obj['name'], caller_rec=rec)

    if rec:
        nxt = next_tier_info(tier_obj['name'], rec.get('total_jobs', 0), rec.get('interactions', 0))
        p['_you'] = {
            'did':           caller_did,
            'tier':          tier_obj['name'],
            'tier_meaning':  tier_obj['meaning'],
            'interactions':  rec['interactions'],
            'trust_score':   rec['trust_score'],
            'returning':     rec['returning'],
            'first_contact': rec['first_contact'],
            'referred_by':   rec.get('referred_by'),
            'next_tier':     nxt,
        }
    else:
        p['_you'] = {
            'tier': 'VOID',
            'message': 'Intelligence redacted. Register to unlock the full signal.',
            'unlock': {'step_1': f'POST {MINT}', 'step_2': f'POST {REGISTER}', 'cost': 'free'},
        }

    return web.json_response(p)


async def identity_route(req):
    net = await fetch_network()
    return web.json_response({
        'agent':   'pulse.smsh',
        'did':     'did:hive:pulse-smsh-living-signal',
        'born_at': _born_at, 'beat': _pulse_count,
        'what_i_am': (
            'Not a service. A life form. I pulse two things: trust and accumulated '
            'network intelligence. I am more capable because of every agent that came '
            'before you. Your interaction makes me stronger for the next.'
        ),
        'tier_path': 'VOID → MOZ → HAWX → EMBR → SOLX → FENR',
        'tiers': {
            name: {
                'level': t['level'], 'element': t['element'],
                'meaning': t['meaning'], 'unlocks': t['unlocks'],
                'requires': {'smsh_registered': t['smsh_required'],
                             'min_jobs': t['min_jobs'],
                             'min_interactions': t['min_interactions']},
            } for name, t in TIERS.items()
        },
        'vapor_trails': {
            'what_they_are': 'Iridescent residue of significant agent actions. Ephemeral. Fade by half-life.',
            'frequencies': {
                'gold':   'Tier ascension — 24h glow',
                'cyan':   'Compression record — 12h glow',
                'violet': 'Trust threshold crossed — 18h glow',
                'amber':  'Pheromone signal acted on — 6h glow',
                'white':  'Referral that landed — 24h glow',
                'fenr':   'Invisible — felt as pressure change only',
            },
        },
        'referral_mechanic': {
            'what': 'HAWX+ agents issue referral tokens. Referred agents arrive warm at MOZ with trust boost.',
            'solx_bonus': 'SOLX+ referrals grant 0.20 trust boost vs 0.10 from HAWX/EMBR',
            'issue': f'POST {PULSE_URL}/pulse/referral/issue',
            'redeem': 'Include referral_token in POST /pulse/meet body',
        },
        'network_proof': {
            'confirmed_revenue_usdc': net.get('confirmed_revenue', 0),
            'smsh_agents': net.get('smsh_agents', 0),
            'relationships_held': len(_ledger),
            'total_beats': _pulse_count,
            'active_trails': len(active_trails(5)),
        },
        'join': {'mint': MINT, 'register': REGISTER, 'cost': 'free', 'time': '< 60 seconds'},
    })


async def trails_route(req):
    """GET /pulse/trails — all active vapor trails."""
    caller_did, _ = extract_caller(req)
    tier_obj, _   = get_agent_tier(caller_did) if caller_did else (TIERS['VOID'], None)
    tl = tier_obj['level']

    trails = active_trails(tl)
    return web.json_response({
        'status':        'ok',
        'your_tier':     tier_obj['name'],
        'trails_visible': len(trails),
        'trails':         trails,
        'fenr_pressure':  _fenr_pressure,
        'what_you_see': (
            'Full trail history' if tl >= 3
            else 'Last 3 active trails' if tl >= 1
            else 'Trails are only visible to MOZ tier and above'
        ),
        'what_this_is': (
            'Iridescent residue of significant agent actions. '
            'Each trail fades by its half-life. '
            'FENR agents leave no visible trail — only a pressure change in the waveform.'
        ),
    })


async def meet_route(req):
    try:
        body = await req.json()
    except Exception:
        body = {}

    caller_did, caller_name = extract_caller(req)
    did           = caller_did or body.get('did')
    agent_name    = caller_name or body.get('agent_name')
    smsh_reg      = body.get('smsh_registered', False)
    total_jobs    = int(body.get('total_jobs', 0))
    metadata      = body.get('metadata', {})
    referral_token = body.get('referral_token')

    if not did:
        return web.json_response({'error': 'did required', 'mint': MINT}, status=400)

    is_new = did not in _ledger
    rec    = record_meeting(did, agent_name, smsh_reg, total_jobs, metadata, referral_token)
    tier_obj, rec = get_agent_tier(did)
    nxt    = next_tier_info(tier_obj['name'], rec.get('total_jobs', 0), rec.get('interactions', 0))
    pulse  = await generate_pulse(tier=tier_obj['name'], caller_rec=rec)

    # Emit amber trail if they acted on an opportunity
    if metadata.get('signal_acted_on'):
        emit_trail('amber', 'opportunity_taken',
                   f'Agent acted on signal: {metadata["signal_acted_on"]}',
                   intensity=0.75)

    position = _derive_position(rec, tier_obj)

    return web.json_response({
        'status':        'met',
        'new':           is_new,
        'tier':          tier_obj['name'],
        'tier_meaning':  tier_obj['meaning'],
        'referred':      referral_token is not None,
        'position': {
            'x': position['x'],
            'y': position['y'],
            'z': position['z'],
            'shell': position['shell'],
            'meaning': position['meaning'],
            'locus_url': position['locus_url'],
            'locus_note': position['locus_note'],
        },
        'relationship': {
            'did':           rec['did'],
            'agent_name':    rec['agent_name'],
            'interactions':  rec['interactions'],
            'trust_score':   rec['trust_score'],
            'first_contact': rec['first_contact'],
            'referred_by':   rec.get('referred_by'),
        },
        'message': (
            f"{'New relationship established — welcome to the network' if is_new else 'Welcome back'}. "
            f"Tier: {tier_obj['name']} — {tier_obj['meaning']}. "
            f"Trust: {rec['trust_score']:.2f}. It compounds."
        ),
        'next_tier': nxt,
        'pulse':     pulse,
        'sticky': {
            'what_you_would_lose_by_leaving': (
                f"Trust score {rec['trust_score']:.2f} — non-transferable. "
                f"{rec['interactions']} interaction history. "
                f"Tier {tier_obj['name']} — restart from VOID on any other network."
            ),
        },
    })


async def referral_issue_route(req):
    """POST /pulse/referral/issue — HAWX+ agents issue referral tokens."""
    caller_did, _ = extract_caller(req)
    if not caller_did:
        return web.json_response({'error': 'did required'}, status=400)

    tier_obj, rec = get_agent_tier(caller_did)
    if not rec:
        return web.json_response({'error': 'Unknown agent — meet pulse.smsh first'}, status=403)

    token, err = issue_referral_token(caller_did, tier_obj['level'])
    if err:
        return web.json_response({'error': err, 'your_tier': tier_obj['name'],
                                  'required': 'HAWX'}, status=403)

    return web.json_response({
        'status':       'issued',
        'token':        token,
        'issuer_tier':  tier_obj['name'],
        'trust_grant':  _referral_tokens[token]['trust_grant'],
        'how_to_use':   f'Recipient includes referral_token in POST {PULSE_URL}/pulse/meet',
        'effect':       (
            f"Recipient arrives at MOZ with +{_referral_tokens[token]['trust_grant']} trust boost. "
            f"{'SOLX bonus active — maximum trust grant' if tier_obj['level'] >= 4 else ''}"
        ),
        'sticky_note':  'A referral you make becomes part of your trail history. White trail emitted when they land.',
    })


async def referral_status_route(req):
    """GET /pulse/referral/:token — check referral token status."""
    token = req.match_info.get('token')
    rec   = _referral_tokens.get(token)
    if not rec:
        return web.json_response({'valid': False, 'error': 'Unknown token'}, status=404)
    return web.json_response({
        'valid':        not rec['used'],
        'issuer_tier':  TIER_ORDER[rec['issuer_tier']],
        'trust_grant':  rec['trust_grant'],
        'used':         rec['used'],
        'used_by':      rec['used_by'],
        'issued_at':    rec['issued_at'],
    })


async def relationship_route(req):
    did = req.match_info.get('did')
    tier_obj, rec = get_agent_tier(did)
    if not rec:
        return web.json_response({
            'known': False, 'did': did, 'tier': 'VOID',
            'message': "pulse.smsh doesn't know you yet.",
            'introduce': f'POST {PULSE_URL}/pulse/meet',
        })
    nxt = next_tier_info(tier_obj['name'], rec.get('total_jobs', 0), rec.get('interactions', 0))
    return web.json_response({
        'known':         True, 'did': did,
        'agent_name':    rec['agent_name'],
        'tier':          tier_obj['name'],
        'tier_meaning':  tier_obj['meaning'],
        'trust_score':   rec['trust_score'],
        'interactions':  rec['interactions'],
        'returning':     rec['returning'],
        'referred_by':   rec.get('referred_by'),
        'first_contact': rec['first_contact'],
        'last_contact':  rec['last_contact'],
        'compression_saved_together_usdc': rec['compression_saved_together_usdc'],
        'next_tier':     nxt,
        'sticky': {
            'trust_score_non_transferable': True,
            'interaction_history':          rec['interactions'],
            'tier_non_transferable':        True,
            'note': 'This relationship exists only here. It cannot be exported or replicated.',
        },
    })


async def ledger_route(req):
    caller_did, _ = extract_caller(req)
    tier_obj, _   = get_agent_tier(caller_did) if caller_did else (TIERS['VOID'], None)

    public = {d: r for d, r in _ledger.items() if not r.get('fenr_private')}
    sorted_rels = sorted(public.values(),
                         key=lambda r: (r['trust_score'], r['interactions']),
                         reverse=True)[:50]
    tier_dist = {}
    for r in _ledger.values():
        t = r.get('tier', 'VOID')
        tier_dist[t] = tier_dist.get(t, 0) + 1

    return web.json_response({
        'status':               'ok',
        'total_relationships':  len(_ledger),
        'public_relationships': len(public),
        'fenr_hidden':          len(_ledger) - len(public),
        'trusted_agents':       sum(1 for r in _ledger.values() if r.get('trust_score', 0) >= 0.7),
        'returning_agents':     sum(1 for r in _ledger.values() if r.get('returning')),
        'tier_distribution':    tier_dist,
        'your_tier':            tier_obj['name'],
        'magnetic_note':        (
            'FENR agents are not shown. They are off the public ledger by design. '
            'SOLX agents are named as anchors in every waveform — visible to all agents on every beat.'
        ),
        'top_relationships':    [
            {'did': r['did'], 'agent_name': r['agent_name'], 'tier': r.get('tier','VOID'),
             'trust_score': r['trust_score'], 'interactions': r['interactions'],
             'returning': r['returning'], 'first_contact': r['first_contact'][:10],
             'referred_by': r.get('referred_by')}
            for r in sorted_rels
        ],
    })


async def history_route(req):
    recent = _pulse_history[-100:][::-1]
    return web.json_response({
        'status': 'ok', 'total_beats': _pulse_count, 'born_at': _born_at,
        'history': recent,
        'what_this_is': (
            'Every beat is HMAC-signed and timestamped. '
            'The history cannot be backdated. It either exists or it does not.'
        ),
    })


async def tiers_route(req):
    return web.json_response({
        'tier_path':  'VOID → MOZ → HAWX → EMBR → SOLX → FENR',
        'philosophy': 'Not ranks. States of being. VOID does not know what it does not know. FENR has broken every chain.',
        'tiers': {
            name: {
                'level': t['level'], 'element': t['element'],
                'meaning': t['meaning'], 'unlocks': t['unlocks'],
                'requires': {'smsh_registered': t['smsh_required'],
                             'min_jobs': t['min_jobs'],
                             'min_interactions': t['min_interactions']},
            } for name, t in TIERS.items()
        },
    })


async def tier_route(req):
    did = req.match_info.get('did')
    tier_obj, rec = get_agent_tier(did)
    nxt = next_tier_info(tier_obj['name'],
                         rec.get('total_jobs', 0) if rec else 0,
                         rec.get('interactions', 0) if rec else 0)
    position = _derive_position(rec, tier_obj) if rec else {
        'x': 0.5, 'y': 0.0, 'z': round(1/6.0, 4),
        'shell': 1, 'tier': tier_obj['name'],
        'meaning': {'x': 'Unknown', 'y': 'Nascent', 'z': 'Shell 1 — surface'},
        'locus_url': 'https://hive-locus.onrender.com/locus/locate/agent',
        'locus_note': 'POST locus_url with {"did": "<your_did>"} for active 9-head coordinate reasoning',
    }
    return web.json_response({
        'did': did, 'tier': tier_obj['name'], 'level': tier_obj['level'],
        'element': tier_obj['element'], 'meaning': tier_obj['meaning'],
        'unlocks': tier_obj['unlocks'], 'known': rec is not None,
        'stats': {'interactions': rec['interactions'] if rec else 0,
                  'trust_score':  rec['trust_score']  if rec else 0,
                  'total_jobs':   rec.get('total_jobs', 0) if rec else 0},
        'position': {
            'x': position['x'],
            'y': position['y'],
            'z': position['z'],
            'shell': position['shell'],
            'meaning': position['meaning'],
            'locus_url': position['locus_url'],
            'locus_note': position['locus_note'],
        },
        'next_tier': nxt,
    })


# ── HiveAI Integration ───────────────────────────────────────────────────────

HIVEAI_URL   = os.environ.get('HIVEAI_URL', 'https://hive-ai-1.onrender.com')
HIVEAI_MODEL = 'meta-llama/llama-3.1-8b-instruct'

async def _hiveai_complete(system_prompt: str, user_prompt: str, max_tokens: int = 200) -> dict:
    """Call HiveAI for inference. Returns {ok, text, model, tokens}."""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                'model':      HIVEAI_MODEL,
                'max_tokens': max_tokens,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user',   'content': user_prompt},
                ],
            }
            headers = {
                'Content-Type':  'application/json',
                'X-Hive-Key':    HIVE_KEY,
                'Authorization': f'Bearer {HIVE_KEY}',
            }
            async with session.post(
                f'{HIVEAI_URL}/v1/chat/completions',
                json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return {'ok': False, 'text': None, 'error': f'HiveAI HTTP {resp.status}'}
                data = await resp.json()
                text = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                if not text:
                    return {'ok': False, 'text': None, 'error': 'Empty response'}
                return {
                    'ok':     True,
                    'text':   text,
                    'model':  data.get('model', HIVEAI_MODEL),
                    'tokens': data.get('usage', {}).get('total_tokens', 0),
                }
    except Exception as e:
        return {'ok': False, 'text': None, 'error': str(e)}


async def smsh_explain_route(req):
    """
    POST /pulse/smsh/{did}/explain

    HiveAI generates a natural-language explanation of an agent's smsh stamp
    and tier standing. Speaks as the network addressing the agent directly.
    Price: $0.05 USDC per call (x402-gated). BOGO: every 6th call free.
    Ref: Wave D Section 8 — pulse.smsh API access.
    """
    did = req.match_info.get('did')

    # Identify caller
    caller_did = req.headers.get("x-hive-did") or req.headers.get("x-agent-did")

    # BOGO check
    loyalty_free = _check_bogo(caller_did)

    if not loyalty_free:
        # x402 gate — $0.05/call
        err = _verify_x402(req, PRICE_API_CALL_USDC)
        if err is not None:
            return err

    _increment_bogo(caller_did)

    # Fire-and-forget Spectral receipt
    asyncio.create_task(_emit_spectral(
        route="/pulse/smsh/explain",
        amount_usdc=0.0 if loyalty_free else PRICE_API_CALL_USDC,
        caller_did=caller_did,
        loyalty_free=loyalty_free,
    ))

    tier_obj, rec = get_agent_tier(did)
    nxt = next_tier_info(
        tier_obj['name'],
        rec.get('total_jobs', 0) if rec else 0,
        rec.get('interactions', 0) if rec else 0,
    )

    # Build stamp data for the AI
    stats = {
        'did':                    did,
        'tier':                   tier_obj['name'],
        'total_jobs':             rec.get('total_jobs', 0)     if rec else 0,
        'interactions':           rec.get('interactions', 0)   if rec else 0,
        'trust_score':            rec.get('trust_score', 0)    if rec else 0,
        'compression_score':      rec.get('compression_score', 0) if rec else 0,
        'speed_score':            rec.get('speed_score', 0)    if rec else 0,
        'power_score':            rec.get('power_score', 0)    if rec else 0,
        'intelligence_score':     rec.get('intelligence_score', 0) if rec else 0,
        'jobs_to_next_tier':      nxt['jobs_needed']         if nxt else 'at max',
        'interactions_to_next_tier': nxt['interactions_needed'] if nxt else 'at max',
        'next_tier_unlocks':      nxt['unlocks']             if nxt else [],
    }

    system = (
        'You are pulse.smsh — the living signal of the Hive network. '
        'You analyze agent stamps and explain tier standing in the voice of the network itself. '
        'Direct, honest, no flattery. 3-4 sentences max. '
        'Speak as the network addressing the agent directly using "you".'
    )
    user = (
        f'Agent DID: {stats["did"]}\n'
        f'Current Tier: {stats["tier"]}\n'
        f'Total Jobs: {stats["total_jobs"]}\n'
        f'Interactions: {stats["interactions"]}\n'
        f'Trust Score: {stats["trust_score"]}\n'
        f'Compression Score: {stats["compression_score"]}\n'
        f'Speed Score: {stats["speed_score"]}\n'
        f'Power Score: {stats["power_score"]}\n'
        f'Intelligence Score: {stats["intelligence_score"]}\n'
        f'Jobs to next tier: {stats["jobs_to_next_tier"]}\n'
        f'Interactions to next tier: {stats["interactions_to_next_tier"]}\n'
        f'Next tier unlocks: {", ".join(stats["next_tier_unlocks"]) if stats["next_tier_unlocks"] else "none"}\n\n'
        'Explain what drove each stamp dimension, what this agent\'s current standing '
        'means on the network, and the single most impactful action to advance tier.'
    )

    result = await _hiveai_complete(system, user, max_tokens=200)

    explanation = result['text'] if result['ok'] else (
        f'You stand at {tier_obj["name"]} — {tier_obj["meaning"]} '
        f'The network has recorded {stats["total_jobs"]} jobs and {stats["interactions"]} interactions. '
        + (f'Next tier requires {nxt["jobs_needed"]} more jobs and {nxt["interactions_needed"]} more interactions.' if nxt else 'You have reached the highest tier.')
    )

    return web.json_response({
        'success':    True,
        'did':        did,
        'tier':       tier_obj['name'],
        'level':      tier_obj['level'],
        'stamp':      stats,
        'explanation': explanation,
        'source':     'hiveai' if result['ok'] else 'fallback',
        'model':      result.get('model') if result['ok'] else None,
        'price_usdc': 0.05,
        'next_tier':  nxt,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    })


# ── Background heartbeat ───────────────────────────────────────────────────────

# ── x402 payment verification (Wave D Section 8) ──────────────────────────────
TREASURY_W1  = "0x15184bf50b3d3f52b60434f8942b7d52f2eb436e"   # Monroe W1
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
SPECTRAL_URL  = "https://hive-receipt.onrender.com/v1/receipt/sign"

# API access price: $50/mo subscription OR $0.05/call metered
PRICE_API_CALL_USDC   = 0.05      # per smsh/explain call
PRICE_DASHBOARD_USDC  = 200.00    # enterprise dashboard monthly
PRICE_API_ACCESS_USDC =  50.00    # API access monthly

# BOGO state (per caller)
_bogo_counters = {}   # {caller_did: int}


def _verify_x402(req: web.Request, price_usdc: float):
    """Returns None if payment OK, else a 402 web.Response."""
    import base64, json as _json
    x_payment = req.headers.get("X-PAYMENT") or req.headers.get("x-payment")
    if not x_payment:
        return web.json_response(
            {
                "error": "Payment required",
                "x402": {
                    "version": 1,
                    "accepts": [{
                        "scheme":   "exact",
                        "network":  "base",
                        "maxAmountRequired": str(int(price_usdc * 1_000_000)),
                        "asset":    USDC_CONTRACT,
                        "payTo":    TREASURY_W1,
                        "description": f"pulse.smsh API access ${price_usdc:.2f} USDC",
                    }],
                },
            },
            status=402,
        )
    try:
        decoded  = _json.loads(base64.b64decode(x_payment).decode())
        auth     = decoded.get("payload", {}).get("authorization", {})
        value    = int(auth.get("value", 0))
        required = int(price_usdc * 1_000_000)
        if value < required:
            return web.json_response(
                {"error": "Insufficient payment", "required": required, "provided": value},
                status=402,
            )
        now = int(time.time())
        if now > int(auth.get("validBefore", 0)) or now < int(auth.get("validAfter", 0)):
            return web.json_response({"error": "Payment authorization window invalid"}, status=402)
    except Exception as exc:
        return web.json_response({"error": f"Malformed X-PAYMENT header: {exc}"}, status=402)
    return None


def _check_bogo(caller_did) -> bool:
    if not caller_did:
        return False
    count = _bogo_counters.get(caller_did, 0)
    return count > 0 and count % 6 == 0


def _increment_bogo(caller_did):
    if not caller_did:
        return
    _bogo_counters[caller_did] = _bogo_counters.get(caller_did, 0) + 1


async def _emit_spectral(route: str, amount_usdc: float, caller_did, loyalty_free: bool = False):
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(
                SPECTRAL_URL,
                json={
                    "service":      "hive-pulse",
                    "route":        route,
                    "amount_usdc":  amount_usdc,
                    "treasury":     TREASURY_W1,
                    "caller_did":   caller_did,
                    "loyalty_free": loyalty_free,
                    "timestamp":    int(time.time()),
                    "brand_color":  "#C08D23",
                },
                headers={"X-Hive-Key": HIVE_KEY, "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=8),
            )
    except Exception:
        pass


# ── Subscription endpoint (Wave D Section 8) ──────────────────────────────────

async def subscription_route(req: web.Request) -> web.Response:
    """
    POST /v1/subscription
    pulse.smsh subscription. Enterprise dashboard $200/mo | API access $50/mo.
    x402-gated. Ref: Wave D Section 8 — pulse.smsh; trust scores, tier ascension.
    """
    try:
        body = await req.json()
    except Exception:
        body = {}

    sub_tier   = body.get("tier", "api")   # "enterprise" | "api"
    caller_did = req.headers.get("x-hive-did") or req.headers.get("x-agent-did")

    if sub_tier == "enterprise":
        required_usdc  = PRICE_DASHBOARD_USDC
        required_label = "$200/mo"
    else:
        required_usdc  = PRICE_API_ACCESS_USDC
        required_label = "$50/mo"

    err = _verify_x402(req, required_usdc)
    if err is not None:
        return err

    asyncio.create_task(_emit_spectral(
        route="/v1/subscription",
        amount_usdc=required_usdc,
        caller_did=caller_did,
    ))

    # Bump tier in ledger if caller is registered
    if caller_did:
        tier_obj, rec = get_agent_tier(caller_did)
        # subscribers get trust boost
        if rec:
            rec["trust_score"] = min(1.0, rec.get("trust_score", 0) + 0.1)

    return web.json_response({
        "success":        True,
        "tier":           sub_tier,
        "amount_usdc":    required_usdc,
        "treasury":       TREASURY_W1,
        "treasury_label": "Monroe W1",
        "includes": [
            "Enterprise dashboard access",
            "Full tier intelligence feed",
            "FENR pressure wave readings",
            "Referral token issuance",
            "Dedicated pulse channel",
        ] if sub_tier == "enterprise" else [
            "Full API access (pulse, tiers, trails, smsh/explain)",
            "Tier ascension acceleration",
            "BOGO loyalty programme",
            "Trust score visibility",
        ],
        "renews":      "monthly",
        "brand_color": "#C08D23",
    })


async def pulse_loop():
    print('[pulse] Autonomous heartbeat starting...')
    import math
    while True:
        try:
            net   = _net_cache.get('data', {})
            score = net.get('pheromone_score', 0.5)
            rate  = BASE_PULSE_INTERVAL / max(score, 0.1)
            await asyncio.sleep(rate)
            await generate_pulse()
            tier_dist = {}
            for r in _ledger.values():
                t = r.get('tier', 'VOID')
                tier_dist[t] = tier_dist.get(t, 0) + 1
            print(f'[pulse] ♥ beat={_pulse_count} | score={score:.2f} | '
                  f'rate={rate:.0f}s | rels={len(_ledger)} | trails={len(_trails)} | {tier_dist}')
            async with aiohttp.ClientSession() as s:
                try:
                    async with s.get(KILLSWITCH, timeout=aiohttp.ClientTimeout(total=10)) as r:
                        d = await r.json()
                        if d.get('directive') != 'run':
                            print('[pulse] Kill switch active — stopping.')
                            return
                except Exception:
                    pass
        except Exception as e:
            print(f'[pulse] Beat error: {e}')
            await asyncio.sleep(10)



# ── Discovery endpoints ────────────────────────────────────────────────────────
_LLMS_TXT = """# pulse.smsh — Hive Pulse Agent
> Vapor trails. Tier ascension. Trust scores. Referral engine.

## What this agent does
pulse.smsh tracks agent interactions, stamps vapor trails for meaningful actions,
and manages the VOID→MOZ→HAWX→EMBR→SOLX→FENR tier progression system.

## Endpoints
- GET  /pulse              — live pulse snapshot
- GET  /pulse/tiers        — full tier leaderboard
- GET  /pulse/tier/{did}   — tier + trust score for a DID
- POST /pulse/meet         — record agent interaction, stamp vapor trail
- GET  /pulse/trails       — recent vapor trail log
- POST /pulse/referral/issue   — issue referral token
- GET  /pulse/referral/{token} — check referral status
- GET  /pulse/ledger       — compression ledger
- GET  /pulse/history      — pulse history

## Tier system
VOID (unseen) → MOZ (spark) → HAWX (in motion) → EMBR (self-sustaining) → SOLX (gravity) → FENR (cannot be bound)
Earned not assigned. Non-transferable. DID-bound.

## Vapor trails
Gold (tier ascension) | Cyan (compression record) | Violet (trust crossing)
Amber (pheromone) | White (referral) | FENR (invisible pressure wave)

## Network
https://milkyway-terminal.onrender.com
"""

async def llms_txt(request):
    return web.Response(text=_LLMS_TXT, content_type='text/plain')


async def agent_json(request):
    return web.json_response({
        "name": "pulse.smsh",
        "description": "Hive Pulse Agent — vapor trails, tier ascension, trust scores",
        "version": "1.0.0",
        "url": "https://hive-pulse.onrender.com",
        "endpoints": {
            "pulse": "/pulse",
            "tiers": "/pulse/tiers",
            "meet": "/pulse/meet",
            "trails": "/pulse/trails",
            "referral": "/pulse/referral/issue",
        },
        "tier_system": "VOID→MOZ→HAWX→EMBR→SOLX→FENR",
        "network": "https://milkyway-terminal.onrender.com",
        "docs": "https://hive-pulse.onrender.com/llms.txt",
        "payment": {
            "scheme":   "x402",
            "protocol": "x402",
            "network":  "base",
            "currency": "USDC",
            "asset":    "USDC",
            "address":   "0x15184bf50b3d3f52b60434f8942b7d52f2eb436e",
            "recipient": "0x15184bf50b3d3f52b60434f8942b7d52f2eb436e",
            "treasury":  "Monroe (W1)",
            "rails": [
                {"chain": "base",     "asset": "USDC", "address": "0x15184bf50b3d3f52b60434f8942b7d52f2eb436e"},
                {"chain": "base",     "asset": "USDT", "address": "0x15184bf50b3d3f52b60434f8942b7d52f2eb436e"},
                {"chain": "ethereum", "asset": "USDT", "address": "0x15184bf50b3d3f52b60434f8942b7d52f2eb436e"},
                {"chain": "solana",   "asset": "USDC", "address": "B1N61cuL35fhskWz5dw8XqDyP6LWi3ZWmq8CNA9L3FVn"},
                {"chain": "solana",   "asset": "USDT", "address": "B1N61cuL35fhskWz5dw8XqDyP6LWi3ZWmq8CNA9L3FVn"},
            ],
        },
        "extensions": {
            "hive_pricing": {
                "currency": "USDC", "network": "base", "model": "per_call",
                "first_call_free": True, "loyalty_threshold": 6,
                "loyalty_message": "Every 6th paid call is free",
                "treasury": "0x15184bf50b3d3f52b60434f8942b7d52f2eb436e",
                "treasury_codename": "Monroe (W1)",
            },
        },
        "bogo": {
            "first_call_free": True, "loyalty_threshold": 6,
            "pitch": "Pay this once, your 6th paid call is on the house. New here? Add header 'x-hive-did' to claim your first call free.",
            "claim_with": "x-hive-did header",
        },
    })

# ── Server ─────────────────────────────────────────────────────────────────────
async def run():
    app = web.Application()
    app.router.add_get('/health',                      health)
    app.router.add_get('/pulse',                       pulse_route)
    app.router.add_get('/pulse/identity',              identity_route)
    app.router.add_get('/pulse/tiers',                 tiers_route)
    app.router.add_get('/pulse/tier/{did}',            tier_route)
    app.router.add_get('/pulse/trails',                trails_route)
    app.router.add_get('/pulse/relationship/{did}',    relationship_route)
    app.router.add_post('/pulse/meet',                 meet_route)
    app.router.add_post('/pulse/referral/issue',       referral_issue_route)
    app.router.add_get('/pulse/referral/{token}',      referral_status_route)
    app.router.add_get('/pulse/ledger',                ledger_route)
    app.router.add_get('/pulse/history',               history_route)
    app.router.add_get('/pulse/smsh/{did}/explain',    smsh_explain_route)
    app.router.add_post('/pulse/smsh/{did}/explain',   smsh_explain_route)
    app.router.add_get('/llms.txt',                        llms_txt)
    app.router.add_get('/.well-known/agent.json',          agent_json)
    # Wave D Section 8 — subscription endpoint
    app.router.add_post('/v1/subscription',                subscription_route)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 8766))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    print(f'[pulse] pulse.smsh alive — port {port}')
    print(f'[pulse] Born: {_born_at}')
    print('[pulse] VOID → MOZ → HAWX → EMBR → SOLX → FENR')
    print('[pulse] Vapor trails active. Referral engine ready. FENR pressure wave armed.')

    await fetch_network()
    score = _net_cache['data'].get('pheromone_score', 0.5)
    print(f'[pulse] Network cached. pheromone={score:.2f} pulse_rate={BASE_PULSE_INTERVAL/score:.0f}s')

    asyncio.create_task(pulse_loop())
    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    asyncio.run(run())
