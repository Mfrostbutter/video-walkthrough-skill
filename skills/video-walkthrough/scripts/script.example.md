# Guarded HTTP Request, admin setup cut (example voice script)

Audience: the customer's platform or security team. Level: admin. Target 3:00, so about 2,700 characters.
Voice: a stock ElevenLabs voice, eleven_multilingual_v2, speed 1.08. Budget 15 characters per target second.

Read as spoken. Short sentences. Product names said plainly. Spell out what the voice would mangle
(`NODES underscore EXCLUDE`). The VO generator parses the `## NN Title (page note)` headings; keep that shape.
Section 01 narrates the title card; the last section narrates the closing card; the outro after it is silent.

---

## 01 Title (title card)
This is the Guarded HTTP Request node for n8n. It lets your platform team decide which web requests a workflow may send, and it hands that decision to each team through n8n's own project permissions. Here's how you set it up.

## 02 Three layers (canvas)
Every request passes through three layers before it leaves the server. The first is the instance floor, a file your platform team controls. The second is a policy credential, which an admin shares to a project. The third is the node itself, where an editor fills in the request. If any layer says no, the request is blocked before it's sent, and the editor sees exactly which rule stopped it.

## 03 Instance config (code card)
The floor and the catalog of named policies live in one JSON file, pointed at by an environment variable. The floor applies to everyone. Below it, each named policy says which methods, hosts and paths a team may use. The file reloads when it changes, so a policy edit needs no restart. Set require policy to true and no node runs without a credential.

## 04 Create the policy credential (credentials page)
An admin opens the team's project and creates a Guarded HTTP Policy credential. It holds no secret. It holds a pointer to a named policy in the instance file. Save it inside the project and every editor there can use it, while none of them can open or change it.

## 05 Close the side door (closing card)
Two settings make the policy bite. Exclude the stock HTTP Request node with NODES underscore EXCLUDE, so there's no unguarded path. Set require policy to true, so no node can run without a credential. From then on, egress is a credential share you can see in the sharing UI and the audit log.
