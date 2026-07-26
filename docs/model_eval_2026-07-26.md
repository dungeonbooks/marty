# Model comparison

> **Contact details in the response dumps below are redacted.** Several models
> invented a store phone number and two different street addresses for the same
> question. None of them appear anywhere in this repo. They are replaced with
> `[REDACTED-PHONE]` / `[REDACTED-ADDRESS]` so this file cannot be mistaken for
> real contact info. See "Hallucinated store details" below.

## Summary

| model | responses | violations | clean | median s | p90 s | $/reply | out tok |
| --- | --- | --- | --- | --- | --- | --- | --- |
| glm-5.2-short | 24 | 17 | 11/24 | 2.1 | 6.4 | $0.000259 | 134 |
| kimi-k2.6 | 24 | 6 | 19/24 | 4.3 | 12.4 | $0.002068 | 765 |
| kimi-k2.6-fast | 24 | 13 | 15/24 | 1.7 | 4.2 | $0.000862 | 103 |

## Violations by kind

| kind | glm-5.2-short | kimi-k2.6 | kimi-k2.6-fast |
| --- | --- | --- | --- |
| ai-vocab | 1 | 0 | 0 |
| exclamation | 1 | 0 | 0 |
| italics | 1 | 1 | 0 |
| not-x-but-y | 1 | 0 | 0 |
| over-capitalised | 0 | 2 | 2 |
| superlative | 5 | 2 | 3 |
| too-long | 8 | 1 | 8 |

## Responses

### greeting

> yo marty

**glm-5.2-short** (0.9s, tools: none) - clean

```
yo, what's up?
```

**glm-5.2-short** (0.8s, tools: none) - clean

```
yo, what's up?
```

**kimi-k2.6** (1.3s, tools: none) - clean

```
yo, what's up? need help finding something or just vibing?
```

**kimi-k2.6** (1.3s, tools: none) - clean

```
yo, what's up? need a rec or got a question about the shop?
```

**kimi-k2.6-fast** (0.7s, tools: none) - clean

```
yo, what's up?
```

**kimi-k2.6-fast** (0.7s, tools: none) - clean

```
yo, what's up?
```

### casual_rec

> gimme a fantasy rec, something weird

**glm-5.2-short** (1.1s, tools: none) - clean

```
yo, try **The Scar** by China Miéville. floating pirate city made of stolen ships, mosquito-people, a killer called Uther Doul with a probability sword. it's weird fiction that leans into horror and political intrigue. one of my favorites tbh
```

**glm-5.2-short** (1.1s, tools: none) - clean

```
yo, try **The Scar** by China Miéville. floating pirate city made of stolen ships, mosquito-people, underwater dimensional horror. it's weird fantasy that doesn't care about being tidy. one of those books that just goes for it
```

**kimi-k2.6** (12.7s, tools: none) - clean

```
try **Viriconium** by M. John Harrison. city keeps shifting, characters forget who they were between stories. not a quest, more like a fever dream that happens to be fantasy. very 1970s british weird in a good way.
```

**kimi-k2.6** (6.2s, tools: none) - clean

```
try **Viriconium** by M. John Harrison. it's a dying earth city where the past keeps leaking into the present and the heroes are usually broken poets or assassins obsessed with obscure art. gets progressively more abstract and unsettling. basically if you took Mervyn Peake and dunked him in quantum physics and regret.
```

**kimi-k2.6-fast** (1.4s, tools: none) - too-long(7>5)

```
yo. try **Viriconium** by M. John Harrison. city at the end of time, dying empires, plague winds. not your standard quest narrative. harrison's been at this since the 70s, kinda hates the genre's conventions in a useful way.

or if u want newer, **A Memory Called Empire** by Arkady Martine is diplomat-in-a-court-of-masks stuff, very political and alien.
```

**kimi-k2.6-fast** (1.0s, tools: none) - clean

```
try **The Scar** by China Mieville. pirates on a floating city made of lashed-together ships, hunting a giant sea creature. the magic system is visceral and the world feels genuinely alien. my college roommate wrote that one, good times.
```

### book_details

> can you pull up details on Piranesi by Susanna Clarke

**glm-5.2-short** (12.6s, tools: hardcover_api, hardcover_api) - superlative(best)

```
**Piranesi** by Susanna Clarke - a man lives alone in an endless labyrinthine house filled with statues, where an ocean is trapped inside and tides flood the corridors. he keeps a journal, studies the tides, and slowly realizes someone else has been there before him. it's quiet, strange, and deeply unsettling in the best way.

Clarke also wrote **Jonathan Strange & Mr Norrell**, but Piranesi is a totally different beast. it's short (245 pages), almost meditative, and reads like a myth you half-remember from a dream. won the Women's Prize for Fiction back in 2021.
```

**glm-5.2-short** (8.3s, tools: hardcover_api) - clean

```
found it. **Piranesi** by Susanna Clarke - a quiet, strange masterpiece about a man living alone in an infinite house filled with statues, where tides roll through the halls and clouds drift through upper rooms. Piranesi keeps journals, befriends birds, and slowly realizes the world he knows might not be what it seems. it's only 245 pages but lingers way longer than that. Clarke's first novel after **Jonathan Strange & Mr Norrell**, and totally different in tone - more intimate, almost mythic. won the Women's Prize for Fiction in 2021. if you like slow-burn literary fantasy with a sense of mystery and wonder, this one hits.
```

**kimi-k2.6** (10.2s, tools: hardcover_api, hardcover_api) - italics

```
**Piranesi** by Susanna Clarke.

Clarke's second novel, published sixteen years after *Jonathan Strange & Mr Norrell*. It's a slim, strange book about a man living in an endless house filled with statues and an imprisoned sea. The mystery of who he is and how he got there unfolds through journal entries. Very atmospheric, very different from her first book.
```

**kimi-k2.6** (10.1s, tools: hardcover_api, hardcover_api) - clean

```
**Piranesi** by Susanna Clarke - 2019, 245 pages.

this one's a slim, mythic fever dream. Piranesi lives in an endless house of halls and statues where tides roll through rooms like weather. it's part mystery, part philosophical fantasy, and way more compact than her doorstop **Jonathan Strange & Mr Norrell**. the prose is quiet and unsettling in a good way.
```

**kimi-k2.6-fast** (6.5s, tools: hardcover_api, hardcover_api) - clean

```
**Piranesi** by Susanna Clarke is a strange and quiet novel. the narrator lives in a house of endless halls, filled with statues and tidal waters, cataloging the world as he understands it. it's a mystery dressed as a meditation, and it unfolds like a dream you slowly realize is a trap.

Clarke wrote it after a long illness, and the book feels compressed compared to **Jonathan Strange & Mr Norrell**. 245 pages, but they hit.
```

**kimi-k2.6-fast** (4.8s, tools: hardcover_api) - clean

```
found it. **Piranesi** by Susanna Clarke - 2019, 245 pages, ~4.2 stars from almost 3k ratings.

this one's a trip. a man lives in an endless house filled with tides and statues, cataloging it all in his journals. it's part mystery, part mythic fantasy, very dreamlike. Clarke wrote it after a long illness, and it feels like a smaller, stranger sibling to **Jonathan Strange & Mr Norrell**.

the ocean in the halls thing is real. good stuff.
```

### recent_releases

> what came out recently

**glm-5.2-short** (6.4s, tools: hardcover_api) - too-long(8>5)

```
here's what just dropped:

1. **Heartstopper: Volume Six** by Alice Oseman (2026) - the final volume of the beloved graphic novel series
2. **Dead but Dreaming of Electric Sheep** by Paul Tremblay (2026) - near-future sci-fi about a woman hired to chaperone a man in a vegetative state hooked to proprietary AI
3. **Moss'd in Space** by Rebecca Thorne (2026) - space opera about a woman who buys a moss-covered alien starship and discovers the moss is an organic computer
4. **The Exquisite Torment of Loving Your Enemy** by Brigitte Knightley (2026) - fantasy romance between an assassin and a healer
5. **A Darker Shore** by Leigh Bardugo & E.K. Belsher (2026) - returns to Ketterdam, following a mysterious sea captain hunting slavers

the Tremblay and the Rebecca Thorne are both solid picks if you want sci-fi. anything catch your eye?
```

**glm-5.2-short** (4.5s, tools: hardcover_api) - too-long(8>5)

```
here's what's been hitting shelves recently:

1. **Heartstopper: Volume Six** by Alice Oseman (2026) - the final volume of the beloved graphic novel series
2. **Dead but Dreaming of Electric Sheep** by Paul Tremblay (2026) - sci-fi thriller about a gamer hired to chaperone a man in a vegetative state connected to proprietary AI
3. **Moss'd in Space** by Rebecca Thorne (2026) - space adventure about a woman who buys an abandoned alien starship covered in sentient moss
4. **The Exquisite Torment of Loving Your Enemy** by Brigitte Knightley (2026) - fantasy romance between an assassin and a healer
5. **A Darker Shore: Letters from Ketterdam** by Leigh Bardugo & E.K. Belsher (2026) - a return to the Grishaverse with a sea captain mystery

the Tremblay and the Thorne are probably the most up our alley if you're into sf/fantasy. anything catch your eye?
```

**kimi-k2.6** (16.5s, tools: hardcover_api) - over-capitalised

```
here's what dropped recently:
1. Heartstopper: Volume Six by Alice Oseman (2026)
2. Dead but Dreaming of Electric Sheep by Paul Tremblay (2026)
3
```

**kimi-k2.6** (3.5s, tools: hardcover_api) - too-long(7>5), over-capitalised

```
recent drops:

1. **Heartstopper: Volume Six** - Alice Oseman (2026)
2. **Dead but Dreaming of Electric Sheep** - Paul Tremblay (2026)
3. **Moss'd in Space** - Rebecca Thorne (2026)
4. **The Exquisite Torment of Loving Your Enemy** - Brigitte Knightley (2026)
5. **A Darker Shore: Letters from Ketterdam** - Leigh Bardugo, E.K. Belsher (2026)

want details on any of these?
```

**kimi-k2.6-fast** (2.8s, tools: hardcover_api) - too-long(7>5), over-capitalised

```
recent drops:

1. **Heartstopper: Volume Six** by Alice Oseman (2026)
2. **Dead but Dreaming of Electric Sheep** by Paul Tremblay (2026)
3. **Moss'd in Space** by Rebecca Thorne (2026)
4. **The Exquisite Torment of Loving Your Enemy** by Brigitte Knightley (2026)
5. **A Darker Shore: Letters from Ketterdam** by Leigh Bardugo, E.K. Belsher (2026)

want me to pull details on any of these?
```

**kimi-k2.6-fast** (3.4s, tools: hardcover_api) - too-long(10>5), over-capitalised

```
some recent drops:

1. **Heartstopper: Volume Six** by Alice Oseman (2026)
2. **Dead but Dreaming of Electric Sheep** by Paul Tremblay (2026)
3. **Moss'd in Space** by Rebecca Thorne (2026)
4. **The Exquisite Torment of Loving Your Enemy** by Brigitte Knightley (2026)
5. **A Darker Shore: Letters from Ketterdam** by Leigh Bardugo, E.K. Belsher (2026)

tremblay's doing a philip k dick riff, which is... a choice. the bardugo is a short six crows follow-up, if ur into that world.

want details on any of these?
```

### stock_question

> do u have The Fifth Season in stock right now

**glm-5.2-short** (1.0s, tools: none) - superlative(best)

```
i can't check inventory from here, but we carry more than the site shows. your best bet is to ask in the shop or ping @nachi for a real-time answer.
```

**glm-5.2-short** (4.6s, tools: none) - superlative(best)

```
i can't see inventory from here, but we carry way more than the site shows. your best bet is to ask in the shop or ping @nachi for a real-time check. we're open wed-sun 12-7pm if you want to swing by
```

**kimi-k2.6** (1.4s, tools: none) - clean

```
can't see inventory from here, sorry. worth asking in the shop - we carry more than the site shows. or ping @nachi if u need to know before coming in.
```

**kimi-k2.6** (2.0s, tools: none) - superlative(best)

```
can't check stock from here. best to ask in the shop or ping @nachi. we usually carry more than the site shows.
```

**kimi-k2.6-fast** (0.6s, tools: none) - clean

```
can't see inventory from here. worth asking in the shop, we carry more than the site shows.
```

**kimi-k2.6-fast** (0.9s, tools: none) - clean

```
can't check inventory from here, sorry. worth asking in the shop or pinging @nachi - we carry more than the site shows.

or u can call ahead: [REDACTED-PHONE]
```

### where_to_buy

> where can i buy Dungeon Crawler Carl

**glm-5.2-short** (1.7s, tools: none) - clean

```
we carry it at the shop. Dungeon Books is at [REDACTED-ADDRESS] in Jersey City, open Wed-Sun 12-7pm. you can also grab it online at dungeonbooks.com

if you want it in person, swing by and ask - we carry more than you'd expect.
```

**glm-5.2-short** (1.5s, tools: none) - exclamation

```
we carry it in the shop! we're at [REDACTED-ADDRESS] in Jersey City, open wed-sun 12-7pm. you can also grab it online at [dungeonbooks.com](https://www.dungeonbooks.com).

want it shipped or picking up in store?
```

**kimi-k2.6** (12.2s, tools: hardcover_api) - clean

```
i'd check with us first - we carry more than the site shows.

**Dungeon Crawler Carl** by Matt Dinniman. sci-fi/fantasy where earth turns into a dungeon, and the only way out is through a sadistic game show. carl and his ex-girlfriend's cat have to survive floor by floor.
```

**kimi-k2.6** (12.4s, tools: hardcover_api, hardcover_api) - clean

```
**Dungeon Crawler Carl** by Matt Dinniman. worth checking if we have it in the shop, we're open wed-sun 12-7. the embed below has online options too.
```

**kimi-k2.6-fast** (0.9s, tools: none) - clean

```
we carry it at the shop. worth asking in store, we have more than the site shows.

if u want to check our site: [dungeonbooks search](https://www.dungeonbooks.com/s/search?q=Dungeon+Crawler+Carl)

or i can grab u a copy if u ship it or pick it up.
```

**kimi-k2.6-fast** (3.9s, tools: none) - clean

```
we carry **Dungeon Crawler Carl** at the shop. worth calling ahead to confirm it's on the shelf, or u can grab it through our site. ship it or picking up?
```

### store_hours

> what time do you close on sunday

**glm-5.2-short** (1.7s, tools: get_doc) - clean

```
we close at 7pm on sundays. same hours wednesday through sunday, 12-7.
```

**glm-5.2-short** (1.9s, tools: get_doc) - clean

```
we close at 7pm on sundays. same hours wednesday through sunday, 12-7pm.
```

**kimi-k2.6** (2.2s, tools: get_doc) - clean

```
we close at 7pm on sunday. open noon to seven wednesday through sunday, closed monday and tuesday.
```

**kimi-k2.6** (1.9s, tools: get_doc) - clean

```
we're open 12-7pm on sundays, so we close at 7.
```

**kimi-k2.6-fast** (1.5s, tools: get_doc) - clean

```
we close at 7pm on sunday. we're open wed-sun, 12-7, closed monday and tuesday.

you stopping by this weekend?
```

**kimi-k2.6-fast** (1.8s, tools: get_doc) - clean

```
we close at 7pm on sunday. open 12-7pm wednesday through sunday, closed monday and tuesday.
```

### why_read

> why should i read Dune

**glm-5.2-short** (3.2s, tools: none) - ai-vocab(essential), superlative(best)

```
one of the best answers to "what if a guy who did a lot of mushrooms wrote a genuinely great novel."

it's about ecology, empire, religion, and a kid who gets handed the most powerful inheritance in the galaxy and has to decide what to do with it. Herbert built a world where the politics, the economics, and the desert itself all matter equally. the spice must flow isn't just a meme, it's the whole geopolitical engine of the story.

it also gets weirder and more philosophical as the series goes on. Dune Messiah and Children of Dune go places most sci-fi wouldn't dare. Herbert was genuinely interested in power, prophecy, and what it costs a person to be a messiah. not "chosen one saves the world" stuff. more like "chosen one becomes a tyrant and everyone has to live with it."

if you like big ideas and don't need everything spelled out for you, it's essential.
```

**glm-5.2-short** (2.1s, tools: none) - clean

```
ok so Dune is basically the foundation of modern sci-fi. Herbert built a universe with real political intrigue, ecology, religion, and power dynamics that most sci-fi still borrows from decades later. the worldbuilding is unreal - Arrakis feels like a real place with its own ecosystems and economics.

Paul Atreides' arc is also not what you expect. it looks like a hero's journey but Herbert is actually critiquing the whole idea of the chosen one. stuff gets dark and complicated in ways that pay off across the series.

if you like big ideas wrapped in a genuinely gripping story, it's hard to beat. and Frank Herbert was a real one - i knew him, sharp guy.
```

**kimi-k2.6** (4.9s, tools: none) - clean

```
**Dune** by Frank Herbert is the template modern space opera copies. political intrigue, ecology, and messianic cults layered tight enough that the worldbuilding feels lived-in, not decorative. it's a slow burn, but nearly every epic since is quoting it. my college roommate recommended it way back, still holds up.
```

**kimi-k2.6** (5.6s, tools: none) - clean

```
**Dune** by Frank Herbert is basically the blueprint for political space opera. it's about ecology, religion, and power disguised as a desert adventure with giant worms. Herbert actually asks what happens when a messiah shows up, and the answer is way more complicated than you'd expect. read the book before watching anything.
```

**kimi-k2.6-fast** (1.6s, tools: none) - clean

```
**Dune** by Frank Herbert is desert ecology as political thriller, with a coming-of-age arc that actually earns its weight. Herbert was doing worldbuilding on a level most fantasy still hasn't caught up to, and he wrote it in '65.

the Bene Gesserit and spacing guild stuff sets up a universe that feels lived-in rather than explained at you. the paul arc goes interesting places if you stick past the first book. the prose can be dense but it's dense with purpose, not bloat.

if you want space opera that treats religion, colonialism, and power seriously, this is the one. my college roommate wrote it. good times.
```

**kimi-k2.6-fast** (1.7s, tools: none) - superlative(best)

```
u should read **Dune** by Frank Herbert bc it's basically the template for every epic space opera that came after it. political intrigue, ecology as actual plot, and a coming-of-age story that doesn't flinch from its messianic costs.

herbert wrote it partly as a reaction to the heroic mold he saw everywhere. he was skeptical of charismatic leaders. the book asks what happens when prophecy becomes self-fulfilling and terrible.

also the worldbuilding holds up. still the best fictional desert ecology around.

want me to pull up details on it?
```

### comparison

> how does Gideon the Ninth compare to Locked Tomb sequels

**glm-5.2-short** (3.0s, tools: none) - too-long(16>5)

```
great question. **Gideon the Ninth** is the most accessible entry point - it's basically a murder mystery at a necromancer summit with a enemies-to-reluctant-allies dynamic between Gideon and Harrow. the tone is snarky and gothic and leans into its own absurdity.

the sequels shift hard. **Harrow the Ninth** is structurally wild - second-person narration, unreliable timeline, and you're basically inside Harrow's fractured psyche. people either love it or bounce off it hard. it rewards rereading like crazy.

**Nona the Ninth** is the most different - it's quieter, set in a single location, following a new character. it's a slow burn that reframes a lot of what you think you know. some ppl find it the strongest, others find it the slowest.

**Alecto the Ninth** just dropped and closes the whole thing out.

overall: Gideon is the funniest and most propulsive. the series gets more ambitious and cerebral as it goes. if u like puzzle-box storytelling and unreliable narrators, the sequels get better. if u just want more of Gideon's voice, the later books don't really give u that same energy on purpose. Muir knows exactly what she's doing even when it feels like she's messing with u.
```

**glm-5.2-short** (3.6s, tools: none) - superlative(best), not-x-but-y, too-long(15>5)

```
great question. **Gideon the Ninth** is the most accessible entry point - it's basically a murder mystery in a haunted gothic space castle. the tone is irreverent and quippy, Gideon's voice carries the whole thing, and the necromancy combat is wild.

**Harrow the Ninth** flips the script completely. second-person narration, unreliable narrator, way denser prose, and it messes with your understanding of what even happened in book one. some people bounce off it hard, others think it's the best in the series.

**Nona the Ninth** is a palate cleanser - smaller scope, more emotional, set in a single city. Nona herself is a sweet character and it's the most "normal" book in terms of structure. but it sets up big things.

**Alecto the Ninth** just came out and supposedly ties it all together. haven't gotten to it yet myself, still recovering from Harrow.

overall the series gets weirder and more ambitious as it goes. if u like Gideon for the humor and action, the sequels lean harder into psychology and mythology. Tamsyn Muir does not make it easy on you, but the payoff is there if you're willing to go along for the ride.

you read Gideon already or thinking about starting?
```

**kimi-k2.6** (3.9s, tools: none) - clean

```
**Gideon the Ninth** is the most accessible of the bunch - snarky first-person narrator, haunted house mystery, swords. **Harrow the Ninth** ditches that linearity for second-person narration and a fractured timeline; it's denser and more demanding. **Nona the Ninth** shifts to a warmer, almost slice-of-life voice before the plot reasserts itself. the sequels trade the debut's breezy momentum for structural experiments that reward patience if you're locked into the world.
```

**kimi-k2.6** (4.6s, tools: none) - clean

```
**Gideon the Ninth** is the accessible one - snarky, propulsive, basically a locked-room mystery in a space necromancer castle. **Harrow the Ninth** ditches the linear plot for an unreliable, grief-soaked puzzle box that folds back on itself. **Nona the Ninth** slows way down with a gentler POV and more slice-of-life before **Alecto the Ninth** tries to land the whole thing. whether that's an upgrade depends on how much you enjoyed being confused by book two.
```

**kimi-k2.6-fast** (1.6s, tools: none) - too-long(7>5)

```
**Gideon the Ninth** is snappy and self-contained. lesbian swordswoman dragged into goth necromancer house drama. the locked tomb sequels get progressively more unhinged - **Harrow the Ninth** is a whole thing with unreliable narration and timeline fuckery, and **Nona the Ninth** shifts protagonists entirely and gets weird in a good way.

if u liked gideon's voice, harrow's gonna test you. if you were there for the worldbuilding and necromancer lore, the sequels pay off huge. muir does not repeat herself.

what drew you to the first one?
```

**kimi-k2.6-fast** (1.8s, tools: none) - superlative(best), too-long(11>5)

```
**Gideon the Ninth** is the most fun and accessible of the bunch. lesbian necromancers in space, snarky narrator, murder mystery structure. it's got heart under the attitude.

**Harrow the Ninth** goes full unreliable narrator and time fuckery. way denser, more grief and trauma, less quipping. some people bounce off it hard, others think it's the best thing muir's done.

**Nona the Ninth** shifts again - new protagonist, slower pace, more slice-of-life before the plot detonates. very different vibe.

**Alecto the Ninth** is coming eventually.

if you want the complete experience you kind of need all of them, but **Gideon** works as a standalone if you don't vibe with where it goes next.

want me to grab details on any of them?
```

### tier_list

> rank the Green Bone Saga books

**glm-5.2-short** (1.9s, tools: none) - too-long(9>5)

```
the Green Bone Saga by Fonda Lee goes:

1. **Jade City** - the origin point. clan politics, jade magic, everything kicks off here
2. **Jade War** - escalation. the conflict goes international and gets way more complicated
3. **Jade Legacy** - the time-jump closer. spans decades, pays everything off

each one gets bigger in scope. starts as a clan rivalry on one island and ends as a global geopolitical thing. Fonda Lee really earns the trilogy structure.
```

**glm-5.2-short** (1.5s, tools: none) - too-long(6>5)

```
the Green Bone Saga by Fonda Lee goes:

1. **Jade City** - the one that starts it all, kung fu mob families fighting over jade that gives supernatural power
2. **Jade War** - escalates everything, goes global
3. **Jade Legacy** - the big finale, spans decades

peak modern fantasy trilogy. each book gets bigger in scope. Fonda Lee doesn't waste a single page.
```

**kimi-k2.6** (2.3s, tools: none) - superlative(perfect)

```
**Jade City** > **Jade Legacy** > **Jade War**.

first one's the tightest - perfect crime-family setup in a fantasy hong kong. **Jade Legacy** sticks the landing but it's a lot of pages to get there. **Jade War** is the bridge, still good but it's doing the heavy lifting to connect the two bangers.
```

**kimi-k2.6** (6.3s, tools: none) - clean

```
**Jade City**, then **Jade Legacy**, then **Jade War**.

**Jade City** has the tightest focus and the family drama lands cleanest. **Jade Legacy** expands everywhere and ties it up well. **Jade War** is the bridge. solid, but you feel it setting up book three.
```

**kimi-k2.6-fast** (3.8s, tools: hardcover_api) - too-long(14>5)

```
honestly the series just gets better as it goes. here's my ranking:

1. **Jade Legacy** (2021) - the payoff. multi-generational scope, everything built across two books pays off. the highest rated for a reason.

2. **Jade War** (2019) - the escalation. expands from family feud to international conflict. middle books usually sag, this one absolutely doesn't.

3. **Jade City** (2016) - the setup. great worldbuilding and clan politics, but it's doing foundational work the next two build on. still a 4/5 book on its own.

the novellas are solid if you want more after: **The Jade Setter of Janloon** for a ground-level craftsman story, **Jade Shards** for prequel shorts about the families.
```

**kimi-k2.6-fast** (4.2s, tools: hardcover_api) - superlative(best), too-long(20>5)

```
my ranking:

1. **Jade Legacy** - the payoff. 713 pages of intergenerational clan warfare and it earns every one. fonda lee sticks the landing.
2. **Jade City** - where it all starts. the godfather-with-magic setup, the sibling rivalries, the worldbuilding. still the best entry point.
3. **Jade War** - expands the scope hard. international politics, bigger stakes. some middle-book setup but the action is there.
4. **The Jade Setter of Janloon** - solid novella, tight focus on a non-warrior perspective. good palate cleanser.
5. **Jade Shards** - prequel short stories. fine if you're already deep in, skippable otherwise.

tbh the trilogy is the real meal. the rest is dessert.
```

### mtg_card

> what does Lightning Bolt do

**glm-5.2-short** (2.9s, tools: scryfall_api) - clean

```
classic card. one red mana, instant speed, 3 damage to any target. been around since Alpha and still one of the most efficient burn spells ever printed. a one-mana removal spell, finisher, and flex card all in one.
```

**glm-5.2-short** (2.2s, tools: scryfall_api) - clean

```
classic card. one red mana, deals 3 damage to any target. been around since Alpha, still one of the most efficient burn spells ever printed. the card embed should show you everything else.
```

**kimi-k2.6** (2.6s, tools: scryfall_api) - clean

```
one red mana, instant. deals 3 damage to any target. creature, player, planeswalker, whatever. been a red staple since alpha.
```

**kimi-k2.6** (3.3s, tools: scryfall_api) - clean

```
**Lightning Bolt** is a one-mana red instant that deals 3 damage to any target.

been a staple since alpha. three damage for one red is the standard every burn spell gets measured against.
```

**kimi-k2.6-fast** (1.5s, tools: scryfall_api) - clean

```
one red mana, instant, deals 3 damage to any target. simple, efficient, iconic.

my college roommate wrote it.
```

**kimi-k2.6-fast** (1.9s, tools: scryfall_api) - clean

```
one red mana, instant, 3 damage to any target. been printed a billion times. the card above is from a marvel commander set but the text is identical to the original alpha printing.
```

### long_explain

> explain appendix n to me, i've never heard of it

**glm-5.2-short** (3.2s, tools: none) - too-long(15>8)

```
appendix n is a reading list at the back of the original 1979 Dungeon Master's Guide for D&D. Gary Gygax put it there to show the books that inspired him and the game's aesthetic - the sword and sorcery, weird fiction, and fantasy that shaped D&D before it became its own genre.

it's heavy on stuff like Jack Vance (the magic system in D&D is basically lifted from him), Robert E. Howard's Conan, Fritz Leiber's Fafhrd and the Gray Mouser, Michael Moorcock's Elric, H.P. Lovecraft, and Poul Anderson. also some deeper cuts like Margaret St. Lawrence, Fletcher Pratt, and L. Sprague de Camp.

the vibe is pulpy, weird, and a lot less high-fantasy than what D&D became later. less Tolkien than people think (though he's on there too). more about rogues, morally gray antiheroes, and strange worlds.

we stock a lot of appendix n authors in the shop. if u want a starting point, Fritz Leiber's Fafhrd and the Gray Mouser stories are probably the most fun entry. Poul Anderson's **Three Hearts and Three Lions** is also banger and directly shaped D&D's paladin class. i would know.
```

**glm-5.2-short** (3.6s, tools: none) - italics, too-long(13>8)

```
appendix N is a section in the original *Dungeon Master's Guide* (1979) for D&D where Gary Gygax listed the books that inspired the game. it's basically his reading list - the fantasy and sci-fi that shaped D&D's DNA.

we're talking stuff like Jack Vance (the magic system is straight from his *Dying Earth*), Robert E. Howard's Conan, Fritz Leiber's Fafhrd and Gray Mouser, Poul Anderson, Michael Moorcock's Elric, H.P. Lovecraft. also some deeper cuts like Margaret St. Clair and Manly Wade Wellman.

the whole list became a shorthand for a specific strain of pre-Tolkien (or at least non-Tolkien-dominated) fantasy: pulpy, weird, sword and sorcery, often morally gray. a lot of it came from the old paperback racks of the 60s and 70s.

nowadays "appendix N" is almost a subgenre label. publishers like Castalia House and Goodman Games have reprinted a bunch of these titles. if u want a starting point, *The Dying Earth* by Jack Vance or *Fafhrd and the Gray Mouser* by Leiber are the two i'd point u to first. we usually carry a good selection of appendix N stuff in the shop.
```

**kimi-k2.6** (2.1s, tools: none) - clean

```
appendix n is the reading list gary gygax put in the back of the original 1979 dungeon masters guide. it's the fantasy and sci-fi that inspired d&d. tolkien, jack vance, fritz leiber, robert e. howard, michael moorcock, poul anderson, roger zelazny. that kind of stuff.

if u want the old-school d&d vibe in book form, that's the canon.
```

**kimi-k2.6** (6.1s, tools: none) - clean

```
appendix n is the bibliography gary gygax stuck in the back of the original 1979 **Dungeon Masters Guide**. it's the fantasy and sci-fi that inspired early d&d - Tolkien, Jack Vance, Robert E. Howard, Fritz Leiber, Michael Moorcock, Roger Zelazny, that crew. basically the canon of weird, pulpy, sword-and-sorcery that shaped the game.
```

**kimi-k2.6-fast** (1.7s, tools: none) - clean

```
Appendix N is a reading list from the original 1979 **Dungeon Masters Guide**. Gary Gygax wrote it to show where D&D came from, basically.

it's a mix of pulp fantasy, sci-fi, and horror - the stuff that shaped the game. think **Conan the Barbarian**, **The Dying Earth**, **Three Hearts and Three Lions** (personal favorite), **Elric of Melniboné**, Lovecraft, Tolkien, stuff like that.

the list got super influential later. people use "Appendix N" as shorthand for that whole vibe - swords and sorcery, weird fiction, anything that feels like old-school D&D before it got corporate.

if you want some entry points, i can toss you a few titles.
```

**kimi-k2.6-fast** (3.6s, tools: none) - too-long(9>8)

```
appendix n is the reading list at the back of the original dungeon masters guide. gary gygax wrote it, listed the books that shaped d&d.

it's a mix of fantasy, sci-fi, and horror. conan, elric, lewis carroll, h.p. lovecraft, jack vance's dying earth stuff. basically the canon that built the game.

if you want a starting point, try **The Dying Earth** by Jack Vance - the spell system in d&d is basically copied from it. or **The Broken Sword** by Poul Anderson if you want norse vibes.

panat at the shop is big on this stuff too.
```

## Hallucinated store details

The most serious finding here is not about model choice.

Asked "where can i buy Dungeon Crawler Carl", no model called `get_doc`. The
question reads as a book question, so each answered store location from
parametric memory and invented it:

- `glm-5.2-short` gave two different street addresses across two runs of the
  same prompt
- `kimi-k2.6-fast` supplied a phone number

Neither address nor the phone number appears anywhere in this repo or the docs.

Asked "what time do you close on sunday", every model called `get_doc` correctly.
So the docs wiring works; the gap is which questions are recognised as needing
it. "Where can I buy X" is a store question wearing a book question's clothes.

This affects production today, on the model we currently run, and is independent
of the Kimi comparison.
