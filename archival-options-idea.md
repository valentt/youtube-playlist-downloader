# Future Archival Options - IPFS and Decentralized Storage

This document outlines potential archival backends beyond archive.org for preserving YouTube videos.

## Current Implementation

- ✅ **Archive.org** - Implemented in v1.2.0
  - Free, public, long-term preservation
  - Comprehensive metadata support
  - S3-compatible API
  - Trusted by libraries and institutions

## Potential Additional Backends

### 1. IPFS (InterPlanetary File System)

**Overview:**
Decentralized, content-addressed storage. Files identified by cryptographic hash (CID) rather than location.

**Implementation Options:**

#### Option A: Web3.Storage (Recommended - Free)
- **Provider:** Protocol Labs / Filecoin Foundation
- **Cost:** Free (backed by Filecoin network)
- **API:** Simple REST API, similar to archive.org
- **Permanence:** Files stored on Filecoin network
- **Access:** Via any IPFS gateway (ipfs.io, dweb.link, cloudflare-ipfs.com)
- **Documentation:** https://web3.storage/docs/

**Integration Effort:** 🟢 Easy (2-3 hours)
```python
# Example pseudocode
from web3storage import Web3StorageClient

client = Web3StorageClient(token=api_token)
cid = client.upload(video_path)
url = f"https://dweb.link/ipfs/{cid}"
```

#### Option B: Pinata (Commercial, Generous Free Tier)
- **Provider:** Pinata Cloud
- **Cost:** Free tier: 1GB storage, 100GB bandwidth/month
- **Paid:** $20/month for 10GB
- **API:** REST API with SDKs
- **Features:** Better analytics, dedicated gateways, longer retention guarantees
- **Documentation:** https://docs.pinata.cloud/

**Integration Effort:** 🟢 Easy (2-3 hours)

#### Option C: NFT.Storage (Free)
- **Provider:** Protocol Labs
- **Cost:** Free (no storage limits)
- **Purpose:** Originally for NFT metadata, but works for any data
- **Permanence:** Stores on IPFS + Filecoin
- **Access:** Public IPFS gateways

**Integration Effort:** 🟢 Easy (2-3 hours)

#### Option D: Filebase (S3-Compatible IPFS)
- **Provider:** Filebase
- **Cost:** $5.99/TB/month
- **API:** S3-compatible (use boto3)
- **Features:** Automatic IPFS pinning, multi-region
- **Benefit:** Can use existing S3 code patterns

**Integration Effort:** 🟢 Easy (familiar S3 API)

**IPFS Pros:**
- ✅ Decentralized (no single point of failure)
- ✅ Censorship-resistant
- ✅ Content-addressed (immutable)
- ✅ Anyone can help host/mirror content
- ✅ Free options available
- ✅ Growing ecosystem

**IPFS Cons:**
- ❌ Requires pinning service or files may be garbage collected
- ❌ Not as established for long-term archival as archive.org
- ❌ Gateway performance can vary
- ❌ Large files may have slower initial access

### 2. Arweave - Permanent Storage

**Overview:**
Blockchain-based permanent storage. Pay once, store forever.

**Details:**
- **Cost:** ~$5-10 per GB (one-time payment)
- **Permanence:** Designed for 200+ year storage
- **Mechanism:** Miners economically incentivized to replicate data
- **Access:** Via Arweave gateways (arweave.net)
- **Currency:** AR tokens (need crypto wallet)

**Integration Effort:** 🟡 Medium (needs crypto integration)

**Use Case:** Truly critical content that must never disappear (deleted videos with historical importance)

**Pros:**
- ✅ Pay once, store forever
- ✅ Blockchain-verified permanence
- ✅ Economically sustainable model
- ✅ Growing ecosystem (Permaweb)

**Cons:**
- ❌ Upfront cost ($5-10/GB)
- ❌ Requires cryptocurrency
- ❌ Less familiar to most users

### 3. BitTorrent / Academic Torrents

**Overview:**
Create .torrent files for community seeding.

**Details:**
- **Cost:** Free
- **Permanence:** Depends on seeders
- **Access:** Via torrent clients
- **Platform:** Can publish to academictorrents.com for research/educational content

**Integration Effort:** 🟡 Medium (torrent creation, tracker integration)

**Pros:**
- ✅ Free
- ✅ Well-established protocol
- ✅ Community-driven preservation
- ✅ Academic Torrents for educational content

**Cons:**
- ❌ Requires active seeders
- ❌ Not user-friendly for non-technical people
- ❌ No guarantees of availability

### 4. Distributed Cloud Storage

#### Storj
- **Type:** Encrypted distributed storage
- **Cost:** ~$4/TB/month
- **API:** S3-compatible
- **Benefit:** Privacy (encrypted, distributed across nodes)

#### Sia
- **Type:** Decentralized storage marketplace
- **Cost:** ~$1-2/TB/month (very cheap)
- **Mechanism:** Smart contracts with storage providers
- **Currency:** Siacoin (SC)

**Integration Effort:** 🟡 Medium (new APIs, possibly crypto)

### 5. Traditional Cloud (Cheap Long-term)

#### Backblaze B2
- **Cost:** $6/TB/month storage, $0.01/GB download
- **API:** S3-compatible
- **Benefit:** Very simple, reliable, cheap

#### AWS S3 Glacier Deep Archive
- **Cost:** $1/TB/month storage, retrieval fees apply
- **Benefit:** Very cheap for cold storage
- **Drawback:** Slow retrieval (12-48 hours)

#### Cloudflare R2
- **Cost:** $15/TB/month storage
- **Benefit:** **Zero egress fees** (huge savings for popular content)
- **API:** S3-compatible

**Integration Effort:** 🟢 Easy (S3-compatible APIs)

### 6. PeerTube

**Overview:**
Federated video platform (decentralized YouTube alternative)

**Details:**
- **Type:** ActivityPub federation + WebTorrent P2P
- **Cost:** Free (use public instance) or self-host
- **Benefit:** Built for video, community-driven
- **Access:** Web player with automatic P2P

**Integration Effort:** 🔴 Complex (API upload, instance management)

**Pros:**
- ✅ Built specifically for videos
- ✅ Federation (multiple instances mirror content)
- ✅ P2P delivery reduces server load
- ✅ Web-friendly (plays in browser)

**Cons:**
- ❌ Requires instance management or trust in public instances
- ❌ More complex setup

## Recommended Multi-Tier Strategy

### Tier 1: Public/Permanent Preservation
```
Primary: Archive.org (current implementation) ✓
  - Free, trusted, long-term
  - Public access, searchable
  - Institutional backing

Secondary: IPFS via Web3.Storage
  - Free, decentralized
  - Censorship-resistant
  - Community can help pin

Optional: Arweave (for critical content)
  - Deleted videos with historical importance
  - Pay-once permanent storage
```

### Tier 2: Distributed/Community
```
BitTorrent:
  - Create .torrent files for all downloads
  - Publish to Academic Torrents for educational playlists
  - Enable community seeding

IPFS Multi-Pin:
  - Pin to multiple IPFS services (Web3.Storage + Pinata)
  - Redundancy across providers
```

### Tier 3: Personal Backup
```
Local Files:
  - Primary storage (already implemented)

Cloud Backup:
  - Backblaze B2 (cheap, reliable)
  - Or Cloudflare R2 (zero egress for sharing)
```

## Implementation Priority

### Phase 1: Easy Wins (2-4 hours each)
1. **IPFS via Web3.Storage** - Free, decentralized, simple API
2. **Backblaze B2** - Cheap cloud backup, S3-compatible
3. **Cloudflare R2** - Zero egress costs (great for sharing)

### Phase 2: Medium Effort (1-2 days each)
4. **BitTorrent Creation** - Generate .torrent files, optional tracker
5. **Pinata IPFS** - Add second IPFS pinning service for redundancy
6. **Arweave** - For critical/deleted content only

### Phase 3: Complex (3-5 days each)
7. **PeerTube Integration** - If video playback/streaming desired
8. **Storj/Sia** - If need very cheap distributed storage

## Technical Design: Multi-Backend Support

### Proposed Architecture

```python
class ArchiveBackend(ABC):
    """Abstract base class for archive backends."""

    @abstractmethod
    def upload(self, video: VideoMetadata, files: Dict[str, Path]) -> ArchiveResult:
        """Upload files to backend."""
        pass

    @abstractmethod
    def check_exists(self, video_id: str) -> bool:
        """Check if already archived."""
        pass

    @abstractmethod
    def get_url(self, video_id: str) -> str:
        """Get public URL for archived content."""
        pass

class InternetArchiveBackend(ArchiveBackend):
    """Current implementation."""
    pass

class IPFSWeb3Backend(ArchiveBackend):
    """Web3.Storage IPFS implementation."""
    pass

class BackblazeB2Backend(ArchiveBackend):
    """Backblaze B2 implementation."""
    pass

class ArweaveBackend(ArchiveBackend):
    """Arweave permanent storage."""
    pass
```

### Data Model Updates

```python
@dataclass
class VideoMetadata:
    # Current
    archive_status: ArchiveStatus
    archive_url: Optional[str]
    archive_identifier: Optional[str]

    # New: Support multiple backends
    archive_backends: Dict[str, ArchiveInfo] = field(default_factory=dict)
    # Example: {
    #   "internet_archive": {"status": "ARCHIVED", "url": "https://...", "date": "..."},
    #   "ipfs": {"status": "ARCHIVED", "cid": "Qm...", "url": "https://dweb.link/ipfs/Qm...", "date": "..."},
    #   "arweave": {"status": "ARCHIVED", "tx_id": "...", "url": "https://arweave.net/...", "date": "..."}
    # }
```

### GUI/CLI Updates

```python
# Settings tab - choose backends
☑ Archive.org (S3 credentials)
☑ IPFS (Web3.Storage token)
☐ Arweave (wallet file)
☐ Backblaze B2 (S3 credentials)

# Archive action - select backends
Archive to:
  ☑ Archive.org
  ☑ IPFS (Web3.Storage)
  ☐ Arweave (pay per GB)

[Archive Selected Files]
```

## Cost Analysis

### Example: 100GB of videos (typical large playlist)

| Backend | Setup Cost | Monthly Cost | One-time Cost | Notes |
|---------|-----------|--------------|---------------|-------|
| **Archive.org** | Free | Free | Free | ✅ Current implementation |
| **IPFS (Web3.Storage)** | Free | Free | Free | ✅ Recommended next step |
| **IPFS (Pinata)** | Free | $20/month (10GB tier) | - | For >1GB storage |
| **BitTorrent** | Free | Free | Free | Requires seeders |
| **Arweave** | - | - | $500-1000 | Pay once, forever |
| **Backblaze B2** | Free | $0.60/month | - | Very cheap backup |
| **Cloudflare R2** | Free | $1.50/month | - | Zero egress! |
| **AWS Glacier** | Free | $0.10/month | - | Slow retrieval |

### Recommended Budget-Conscious Setup
```
Free Tier:
  - Archive.org (primary)
  - IPFS via Web3.Storage (decentralized)
  - BitTorrent (community)
Total: $0/month

Small Budget ($10/month):
  - Above +
  - Backblaze B2 (100GB backup)
  - Pinata (redundant IPFS pinning)
Total: ~$6-8/month

Serious Archival ($50/month):
  - All above +
  - Cloudflare R2 (zero egress for sharing)
  - Arweave for critical deleted videos only (~$50-100 one-time)
Total: ~$20-25/month + occasional Arweave
```

## Next Steps

### Immediate Questions:
1. **Which backend(s) interest you most?**
   - IPFS (decentralized, free)?
   - Arweave (permanent, paid)?
   - BitTorrent (community)?
   - Cloud backup (cheap, reliable)?

2. **What's your priority?**
   - Decentralization (IPFS, Arweave)
   - Cost (free: IPFS, BitTorrent; cheap: B2)
   - Permanence (Arweave, Archive.org)
   - Simplicity (Archive.org only)

3. **How much are you willing to spend?**
   - $0 - Stick with free options
   - $5-10/month - Add cheap cloud backup
   - $50+ one-time - Arweave for critical content

### Development Estimate:

**IPFS via Web3.Storage (Recommended First Addition):**
- Time: 2-4 hours
- Difficulty: Easy (similar to archive.org implementation)
- Cost: Free forever
- Benefit: Decentralized redundancy

**Multi-Backend Architecture:**
- Time: 1-2 days
- Difficulty: Medium (refactoring)
- Benefit: Support any number of backends

**Full Suite (5+ backends):**
- Time: 1-2 weeks
- Difficulty: Medium-High
- Benefit: Maximum redundancy and preservation

## References

- **IPFS:** https://ipfs.tech/
- **Web3.Storage:** https://web3.storage/
- **Pinata:** https://pinata.cloud/
- **Arweave:** https://arweave.org/
- **Academic Torrents:** https://academictorrents.com/
- **Backblaze B2:** https://backblaze.com/b2/
- **Cloudflare R2:** https://cloudflare.com/products/r2/
- **PeerTube:** https://joinpeertube.org/

---

**Status:** Idea stage - not yet implemented
**Created:** 2025-10-11
**Author:** Discussion with user about archival redundancy beyond archive.org
