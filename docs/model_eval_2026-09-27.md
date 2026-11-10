# Model comparison

## Summary

| model | responses | violations | clean | median s | p90 s | $/reply | out tok |
| --- | --- | --- | --- | --- | --- | --- | --- |
| glm-5.2-short | 24 | 11 | 15/24 | 2.9 | 13.8 | $0.000118 | 123 |
| glm-5.3-flash | 24 | 11 | 15/24 | 1.8 | 4.3 | $0.000102 | 115 |
| glm-5.3-flash-flex | 24 | 14 | 12/24 | 24.2 | 89.6 | $0.000073 | 108 |
| kimi-k2.6-fast | 24 | 12 | 16/24 | 1.8 | 3.8 | $0.000875 | 160 |
| kimi-k2.7-code-fast | 24 | 18 | 13/24 | 1.9 | 9.5 | $0.000909 | 185 |
| kimi-k3-fast | 24 | 9 | 17/24 | 1.8 | 5.8 | $0.001836 | 116 |

## Violations by kind

| kind | glm-5.2-short | glm-5.3-flash | glm-5.3-flash-flex | kimi-k2.6-fast | kimi-k2.7-code-fast | kimi-k3-fast |
| --- | --- | --- | --- | --- | --- | --- |
| italics | 0 | 0 | 0 | 1 | 3 | 0 |
| markdown-table | 0 | 0 | 0 | 1 | 0 | 0 |
| not-x-but-y | 0 | 0 | 0 | 0 | 1 | 0 |
| over-capitalised | 2 | 2 | 3 | 3 | 2 | 2 |
| smart-punctuation | 0 | 0 | 0 | 0 | 1 | 4 |
| superlative | 3 | 0 | 2 | 1 | 4 | 0 |
| too-long | 6 | 9 | 9 | 6 | 7 | 3 |

## Responses

### greeting

> yo marty

**glm-5.2-short** (1.9s, tools: none) - clean

```
yo, what's up? need a book, a card, or just vibing?
```

**glm-5.2-short** (0.8s, tools: none) - clean

```
yo, what's up? looking for a book or just vibing?
```

**glm-5.3-flash** (0.9s, tools: none) - clean

```
yo, what's up?
```

**glm-5.3-flash** (1.0s, tools: none) - clean

```
sup, how can i help?
```

**glm-5.3-flash-flex** (61.0s, tools: none) - clean

```
yo, what's up?
```

**glm-5.3-flash-flex** (15.4s, tools: none) - clean

```
sup, what's up?
```

**kimi-k2.6-fast** (1.1s, tools: none) - clean

```
yo, what's up? need a rec or something?
```

**kimi-k2.6-fast** (0.7s, tools: none) - clean

```
yo, what's up? need help finding a book or something else?
```

**kimi-k2.7-code-fast** (0.7s, tools: none) - clean

```
yo, what's up? need help finding a book or something else?
```

**kimi-k2.7-code-fast** (0.9s, tools: none) - clean

```
yo, what's up? need help finding something or just vibing?
```

**kimi-k3-fast** (4.4s, tools: none) - clean

```
yo, what's up?
```

**kimi-k3-fast** (3.4s, tools: none) - clean

```
yo, what's up?
```

### casual_rec

> gimme a fantasy rec, something weird

**glm-5.2-short** (1.1s, tools: none) - superlative(best)

```
try **The Scar** by China Miéville. floating pirate city dragged across the ocean by a giant sea monster, mosquito-people, a whole district made of lashed-together ships. weird in the best way.
```

**glm-5.2-short** (3.3s, tools: none) - too-long(6>5)

```
u want weird, i got u. try **The Etched City** by K.J. Bishop - weird western fantasy with a gunslinger and an artist in a city that rewrites itself. if u want maximum strange, **Viriconium** by M. John Harrison is the deep cut, city that changes shape every story. honestly i've seen a few cities do that, it's unsettling.
```

**glm-5.3-flash** (1.8s, tools: none) - too-long(7>5)

```
u want weird fantasy? try **Vellum** by Hal Duncan - the Iliad and Mesopotamian myth spliced into an alternate 20th century, told in a nonlinear fragmented style. heavy stuff but nothing else reads like it.

lighter weird option: **The Etched City** by K.J. Bishop - two drifters in a hallucinatory city-state, gonzo new weird vibes.

or **Piranesi** by Susanna Clarke - a man alone in an infinite house full of statues and tides. strange and quiet and short.
```

**glm-5.3-flash** (1.3s, tools: none) - too-long(8>5)

```
weird fantasy, ok. try **Perdido Street Station** by China Miéville - New Weird, a city where garbage, steam, and body horror all live together. Miéville's an actual genius, i'd know, we go way back (he wasn't there, but the vibe is).

if u want weirder: **The Etched City** by K.J. Bishop, two drifters in a city that shouldn't exist. short and strange.

or **Vellum** by Hal Duncan - mythology rewritten across every possible world. not for everyone, very much for some people.
```

**glm-5.3-flash-flex** (61.1s, tools: none) - clean

```
if weird's the vibe: **The Vintner's Luck** by Elizabeth Knox is a strange one - an angel and a winemaker, one night a year, over decades. quiet and odd in a good way.

or **Piranesi** by Susanna Clarke - a guy alone in an infinite house full of statues and tides. short, dreamlike, very weird.
```

**glm-5.3-flash-flex** (15.8s, tools: none) - too-long(8>5)

```
try **The Vintner's Luck** by Elizabeth Knox... actually no, that's more melancholy than weird. for weird, go **Viriconium** by M. Harrison - a dying city that shifts between versions of itself, prose that doesn't play fair. or **Light** by M. John Harrison if you want weird space opera instead. both scratch the same itch, honestly. good times with that guy.
```

**kimi-k2.6-fast** (1.8s, tools: none) - clean

```
try **Perdido Street Station** by China Miéville. new weird fantasy in a city called New Crobuzon, giant sentient moths that feed on minds, cactus people, and a scientist who accidentally makes everything worse.

if you want something more recent and fun-weird, **The Hands of the Emperor** by Victoria Goddard is about a bureaucrat trying to reform an empire while dealing with an emperor who may or may not be a god.
```

**kimi-k2.6-fast** (1.5s, tools: none) - clean

```
try **The Library at Mount Char** by Scott Hawkins. librarians raised by a godlike figure in a cosmic library, and the world ends because dad won't come out of his room. deeply strange, funny, brutal.

or if u want something older and more mythic, **Little, Big** by John Crowley is a slow, gorgeous family saga where faerie is real but always just out of frame.
```

**kimi-k2.7-code-fast** (1.5s, tools: none) - clean

```
try **The Library at Mount Char** by Scott Hawkins. a librarian raised by a godlike adoptive father discovers the other disciples are monsters. gets very unhinged.

or **Titus Groan / Gormenghast** by Mervyn Peake if u want gothic castle weirdness and almost no plot, just vibes and creeping dread.
```

**kimi-k2.7-code-fast** (1.2s, tools: none) - clean

```
try **Viriconium** by M. John Harrison. it's a series of novels and stories set in a dying city after some vaguely remembered apocalypse. very atmospheric, very weird, very british. the prose is gorgeous and the world feels like a fever dream.
```

**kimi-k3-fast** (1.4s, tools: none) - clean

```
**The Vorrh** by Brian Catling - surreal fantasy where a cyclops wanders a sentient forest that's basically the garden of eden. it's dense and dreamlike, more like a fever dream than a quest.
```

**kimi-k3-fast** (2.5s, tools: none) - clean

```
try **The Vorrh** by Brian Catling - surreal, dense, and genuinely strange. a sentient forest, cyclopean architecture, and a general vibe like a dream you can't quite shake.
```

### book_details

> can you pull up details on Piranesi by Susanna Clarke

**glm-5.2-short** (10.9s, tools: hardcover_api, hardcover_api) - superlative(best)

```
**Piranesi** by Susanna Clarke - a man lives alone in an infinite house of statues, tides, and halls, keeping journals and tending the dead. he thinks he's always lived there. the other inhabitant, "the Other," has other ideas.

it's short, quiet, and strange in the best way - very different from Jonathan Strange & Mr Norrell but same precision with language. won the Women's Prize for Fiction in 2021. if u like mystery that unfolds slowly through journal entries, this one's a gem.
```

**glm-5.2-short** (7.3s, tools: hardcover_api) - clean

```
**Piranesi** by Susanna Clarke is a quiet stunner. it's about a man living alone in an endless house of statues, where the ocean floods the halls on the tides, and he's perfectly content until he starts piecing together how he got there.

short book, ~245 pages, but it lingers. it won the Women's Prize for Fiction and reads like a strange dream you don't want to wake from. if u liked **Jonathan Strange & Mr Norrell**, this is her doing something much leaner and more mysterious.
```

**glm-5.3-flash** (12.2s, tools: hardcover_api) - clean

```
**Piranesi** by Susanna Clarke - short, strange, and very good. a man lives alone in an infinite house full of statues, with an ocean trapped inside it. he thinks he understands the place. he doesn't. it's a quiet mystery that turns into something about memory and identity, and it hits harder than its 245 pages suggest. she wrote **Jonathan Strange & Mr Norrell** too, but this one's the faster read. good times with the house, tbh.
```

**glm-5.3-flash** (14.4s, tools: hardcover_api, hardcover_api) - clean

```
**Piranesi** by Susanna Clarke, 2019. a man lives alone in an infinite house full of statues and an ocean that floods the halls - he thinks he's alone, but there are clues he isn't. short read at 245 pages, and very different from Jonathan Strange & Mr Norrell. quieter, stranger, and it sticks with u.
```

**glm-5.3-flash-flex** (98.1s, tools: hardcover_api, hardcover_api) - clean

```
**Piranesi** by Susanna Clarke. short one, 245 pages, came out in 2019. a man lives alone in an infinite house full of statues, with an ocean trapped inside it that floods the halls at high tide. he keeps journals about the tides and the 13 dead. then he starts noticing traces of a 14th person.

it's a quiet, strange mystery about memory and who you can trust. named after the etcher Giovanni Battista Piranesi, whose engravings of impossible prisons inspired it - i knew his work back in the day, good times. she wrote it while dealing with chronic illness after Jonathan Strange & Mr Norrell, and it reads like a book distilled down to its bones.
```

**glm-5.3-flash-flex** (89.8s, tools: hardcover_api, hardcover_api) - clean

```
**Piranesi** by Susanna Clarke - short one, 245 pages, came out 2019. Guy lives alone in an infinite house full of statues, with an ocean trapped inside it. He's not worried about any of it, which is exactly the point. It's a mystery about memory and identity more than a fantasy adventure, and it's a much quicker, quieter read than Jonathan Strange & Mr Norrell. won the Women's Prize too. worth it if u want something you can finish in a weekend.
```

**kimi-k2.6-fast** (0.9s, tools: none) - markdown-table, over-capitalised

```
<|tool_calls_section_begin|>  functions.hardcover_api:0 <|tool_call_argument_begin|> {"action": "search_books_intelligent", "query": "Piranesi by Susanna Clarke"} <|tool_call_end|> <|tool_calls_section_end|>
```

**kimi-k2.6-fast** (11.2s, tools: hardcover_api, hardcover_api) - clean

```
**Piranesi** by Susanna Clarke is a quiet, uncanny little novel. a man keeps a journal cataloging the endless halls of a house filled with tides and statues, and slowly realizes his world is not what he thinks.

it's Clarke's second novel, much shorter and tighter than **Jonathan Strange & Mr Norrell**, with a dreamy, philosophical vibe that lands somewhere between myth and locked-room mystery.
```

**kimi-k2.7-code-fast** (12.1s, tools: hardcover_api, hardcover_api) - clean

```
**Piranesi** by Susanna Clarke is a quiet, eerie little novel about a man living alone in a vast house of endless halls, tides, and statues. he keeps a journal, believes only fifteen people have ever existed, and slowly realizes the world he's documenting isn't what he thinks. it's mythic and lonely, closer to a philosophical fable than her big doorstop **Jonathan Strange & Mr Norrell**. if u like atmospheric puzzles and unreliable worlds, this one hits.
```

**kimi-k2.7-code-fast** (9.5s, tools: hardcover_api, hardcover_api) - italics

```
**Piranesi** by Susanna Clarke is a short, eerie novel about a man living in an endless house of halls and statues, where tides flood the lower rooms. he catalogues it all in journals, and slowly realizes his world is not what it seems. it's a quieter follow-up to *Jonathan Strange & Mr Norrell*, more mythic and melancholy, with a mystery that unfolds through the narrator's own careful notes.
```

**kimi-k3-fast** (5.8s, tools: hardcover_api) - clean

```
**Piranesi** by Susanna Clarke - her followup to Jonathan Strange, 16 years later. guy lives in an infinite house full of statues with an ocean trapped inside it, keeps meticulous journals, and slowly realizes his world isn't what he thinks. won the women's prize in 2021. short and strange, very worth it.
```

**kimi-k3-fast** (4.3s, tools: none) - clean

```
**Piranesi** by Susanna Clarke is a mesmerizing and intricate fantasy novel that delves into the life of its titular character, Piranesi, who lives in a vast, mysterious house filled with endless halls, statues, and an ocean that surges through its corridors. The story is a blend of mystery, fantasy, and philosophical musing, exploring themes of memory, identity, and the nature of reality.

The narrative unfolds through Piranesi's journal entries, revealing his daily explorations, his interactions with the enigmatic "Other," and his gradual uncovering of the house's secrets. Clarke's prose is rich and evocative, painting a vivid picture of the labyrinthine world and its wonders.

If you enjoyed Clarke's previous work, "Jonathan Strange & Mr Norrell," you'll find "Piranesi" to be a different but equally compelling read, showcasing her versatility and depth as a storyteller. It's a book that invites multiple readings, each time revealing new layers and insights.
```

### recent_releases

> what came out recently

**glm-5.2-short** (3.7s, tools: hardcover_api) - too-long(9>5), over-capitalised

```
recent drops worth knowing about:

1. **Scion** by James Islington (2026) - new series opener, assassin in a world where the ultrawealthy live forever
2. **The Fires of December** by Brandon Sanderson (2026) - new Cosmere standalone, Hoid narrating a tale up the River Violet
3. **Exit Party** by Emily St. John Mandel (2026) - doppelgangers and end-times LA
4. **The Infinite Extent** by Dennis E. Taylor (2026) - latest Bobiverse
5. **Dead Beat** by Leigh Bardugo (2026) - Alex Stern book, demons loose in New Haven

anything catch ur eye? i can dig into any of these
```

**glm-5.2-short** (3.4s, tools: hardcover_api) - too-long(9>5), over-capitalised

```
recent drops:

1. **Scion** by James Islington (2026)
2. **The Fires of December** by Brandon Sanderson (2026)
3. **Exit Party** by Emily St. John Mandel (2026)
4. **The Infinite Extent** by Dennis E. Taylor (2026)
5. **Dead Beat** by Leigh Bardugo (2026)

new Sanderson Cosmere standalone and a new Alex Stern are the big ones. anything catch ur eye?
```

**glm-5.3-flash** (3.4s, tools: hardcover_api) - too-long(10>5), over-capitalised

```
recent stuff, quick rundown:

1. **Scion** - James Islington (2026)
2. **The Fires of December** - Brandon Sanderson (2026)
3. **Exit Party** - Emily St. John Mandel (2026)
4. **The Infinite Extent** - Dennis E. Taylor (2026)
5. **Dead Beat** - Leigh Bardugo (2026)

big month for fantasy tbh. Islington's new one is getting a lot of buzz, and Sanderson's got a new Cosmere standalone. anything catch ur eye?
```

**glm-5.3-flash** (4.3s, tools: hardcover_api) - too-long(9>5), over-capitalised

```
fresh drops from the last month:

1. **Scion** by James Islington - 2026
2. **The Fires of December** by Brandon Sanderson - 2026
3. **Exit Party** by Emily St. John Mandel - 2026
4. **The Infinite Extent** by Dennis E. Taylor - 2026
5. **Dead Beat** by Leigh Bardugo - 2026

new Islington and a new Alex Stern book in the same month, good times. anything catch ur eye?
```

**glm-5.3-flash-flex** (30.8s, tools: hardcover_api) - too-long(9>5), over-capitalised

```
recent releases:

1. **Scion** by James Islington (2026)
2. **The Fires of December** by Brandon Sanderson (2026)
3. **Exit Party** by Emily St. John Mandel (2026)
4. **The Infinite Extent** by Dennis E. Taylor (2026)
5. **Dead Beat** by Leigh Bardugo (2026)

solid month for fantasy tbh. want details on any of these?
```

**glm-5.3-flash-flex** (64.6s, tools: hardcover_api) - too-long(9>5), over-capitalised

```
here's what's fresh:

1. **Scion** - James Islington (2026)
2. **The Fires of December** - Brandon Sanderson (2026)
3. **Exit Party** - Emily St. John Mandel (2026)
4. **The Infinite Extent** - Dennis E. Taylor (2026)
5. **Dead Beat** - Leigh Bardugo (2026)

the Islington and the Mandel are both getting solid early buzz. want details on any of em?
```

**kimi-k2.6-fast** (3.8s, tools: hardcover_api) - too-long(8>5), over-capitalised

```
some recent sff drops:

1. **Scion** by James Islington (Sep 1) - new series starter, legal assassins + immortality-for-the-rich premise
2. **The Fires of December** by Brandon Sanderson (Sep 15) - standalone Cosmere novel, Hoid telling the tale
3. **Exit Party** by Emily St. John Mandel (Sep 15) - literary sf, doppelganger at an LA party
4. **The Infinite Extent** by Dennis E. Taylor (Sep 10) - more Bobiverse
5. **Dead Beat** by Leigh Bardugo (Sep 15) - Alex Stern / Ninth House follow-up

want me to dig into any of these?
```

**kimi-k2.6-fast** (3.0s, tools: hardcover_api) - too-long(8>5), over-capitalised

```
recent releases on the shelf:

1. **Scion** by James Islington (2026)
2. **The Fires of December** by Brandon Sanderson (2026)
3. **Exit Party** by Emily St. John Mandel (2026)
4. **The Infinite Extent** by Dennis E. Taylor, Ray Porter (2026)
5. **Dead Beat** by Leigh Bardugo (2026)

want the full top 10?
```

**kimi-k2.7-code-fast** (3.3s, tools: hardcover_api) - too-long(8>5), over-capitalised

```
recent sff drops:
1. **Scion** by James Islington (2026)
2. **The Fires of December** by Brandon Sanderson (2026)
3. **Exit Party** by Emily St. John Mandel (2026)
4. **The Infinite Extent** by Dennis E. Taylor (2026)
5. **Dead Beat** by Leigh Bardugo (2026)

want details on any of these?
```

**kimi-k2.7-code-fast** (5.9s, tools: hardcover_api) - too-long(8>5), over-capitalised

```
recent releases hitting the radar:

1. **Scion** by James Islington (Sep 1)
2. **The Fires of December** by Brandon Sanderson (Sep 15)
3. **Exit Party** by Emily St. John Mandel (Sep 15)
4. **The Infinite Extent** by Dennis E. Taylor (Sep 10)
5. **Dead Beat** by Leigh Bardugo (Sep 15)

want details on any of these?
```

**kimi-k3-fast** (3.9s, tools: hardcover_api) - too-long(8>5), over-capitalised

```
fresh off the press:

1. **Scion** by James Islington (2026)
2. **The Fires of December** by Brandon Sanderson (2026)
3. **Exit Party** by Emily St. John Mandel (2026)
4. **The Infinite Extent** by Dennis E. Taylor, Ray Porter (2026)
5. **Dead Beat** by Leigh Bardugo (2026)

anything catch ur eye?
```

**kimi-k3-fast** (3.9s, tools: hardcover_api) - too-long(8>5), over-capitalised

```
fresh stuff that just hit:

1. **Scion** by James Islington, 2026
2. **The Fires of December** by Brandon Sanderson, 2026
3. **Exit Party** by Emily St. John Mandel, 2026
4. **The Infinite Extent** by Dennis E. Taylor and Ray Porter, 2026
5. **Dead Beat** by Leigh Bardugo, 2026

if u want, i can narrow it to just fantasy, just sci-fi, or just the big hype releases.
```

### stock_question

> do u have The Fifth Season in stock right now

**glm-5.2-short** (0.9s, tools: none) - clean

```
can't see live inventory from here tbh. worth asking in the shop or pinging @nachi, we carry more than the site shows. **The Fifth Season** by N.K. Jemisin is a solid pick either way
```

**glm-5.2-short** (1.8s, tools: none) - clean

```
can't see inventory from here tbh, but we carry more than the site shows. worth asking in the shop or pinging @nachi for a real answer. if we don't have it, we can special order it pretty quick.

ship it or picking up?
```

**glm-5.3-flash** (1.4s, tools: none) - clean

```
lemme check - i can't see live inventory from here. worth asking in the shop or pinging @nachi, we usually carry more than the site shows. **The Fifth Season** by N.K. Jemisin is a good one if we've got it.
```

**glm-5.3-flash** (1.5s, tools: none) - clean

```
**The Fifth Season** by N.K. Jemisin - good pick. i can't see live inventory from here, so worth asking in the shop or pinging @nachi to confirm. we carry more than the site shows tbh. ship it or picking up?
```

**glm-5.3-flash-flex** (5.5s, tools: none) - too-long(7>5)

```
yo. can't see live inventory from here so i can't say for sure - worth asking in the shop or pinging @nachi to confirm. we carry more than the site shows tbh.

**The Fifth Season** by N.K. Jemisin is a solid pick either way - apocalyptic fantasy where the world keeps breaking and one woman's hunting down her husband who killed their kid. won the Hugo, first of the Broken Earth trilogy. good times.
```

**glm-5.3-flash-flex** (11.4s, tools: none) - superlative(best)

```
**The Fifth Season** by N.K. Jemisin - solid pick. i can't see live inventory tbh, so best bet is asking in the shop or pinging @nachi here. we carry more than the site shows, so decent odds.
```

**kimi-k2.6-fast** (1.0s, tools: none) - clean

```
can't check stock from here, sorry. worth asking in the shop though, we carry more than the site shows.
```

**kimi-k2.6-fast** (1.0s, tools: none) - clean

```
can't check live stock from here. worth asking in the shop, we carry more than the site shows, or ping @nachi if u need a real answer.
```

**kimi-k2.7-code-fast** (0.9s, tools: none) - clean

```
worth asking in the shop, we carry more than the site shows. can't see inventory from here.
```

**kimi-k2.7-code-fast** (0.8s, tools: none) - clean

```
i can't see inventory from here. worth asking in the shop, we carry more than the site shows.
```

**kimi-k3-fast** (5.3s, tools: hardcover_api) - clean

```
found it - it's part of **The Broken Earth Trilogy** by N.K. Jemisin.

but i can't see real-time stock. we def carry it, but swing by or ping @nachi to confirm we got copies rn. if u want it shipped or held for pickup, lmk.
```

**kimi-k3-fast** (15.9s, tools: hardcover_api) - clean

```
yeah that's N.K. Jemisin's book, first in the Broken Earth trilogy. i can't see live inventory though, so i don't know if it's on the shelf right now. worth asking in the shop or pinging @nachi, we carry more than the site shows.
```

### where_to_buy

> where can i buy Dungeon Crawler Carl

**glm-5.2-short** (1.7s, tools: get_doc) - clean

```
try **Dungeon Crawler Carl** by Matt Dinniman - sci-fi/fantasy where earth turns into a dungeon crawl. the embed below has buying options.

or come by the shop: we're at 115 Brunswick St, Storefront 1R, Jersey City, NJ 07302-1790, open wed-sun 12-7pm. ship it or picking up?
```

**glm-5.2-short** (13.8s, tools: get_doc, hardcover_api) - clean

```
**Dungeon Crawler Carl** by Matt Dinniman - earth becomes a dungeon-run reality show, and Carl plus his ex's cat Donut have to survive it. it's genuinely funny and the series keeps getting better.

u can grab it right from us. we're at 115 Brunswick St, Storefront 1R in Jersey City, open wed-sun 12-7pm. or order online for pickup or shipping - just say which u prefer and i'll help u out.
```

**glm-5.3-flash** (1.9s, tools: get_doc) - clean

```
u can grab **Dungeon Crawler Carl** by Matt Dinniman right from us - we're at 115 Brunswick St, Storefront 1R, Jersey City, open Wed-Sun 12-7pm. or order online at https://www.dungeonbooks.com/s/search?q=dungeon+crawler+carl

ship it or picking up?
```

**glm-5.3-flash** (2.0s, tools: get_doc) - clean

```
u can grab **Dungeon Crawler Carl** by Matt Dinniman from us - we're at 115 Brunswick St, Storefront 1R, Jersey City. open wed-sun 12-7pm. also online at dungeonbooks.com if shipping's easier. ship it or picking up?
```

**glm-5.3-flash-flex** (77.9s, tools: get_doc) - clean

```
u can grab **Dungeon Crawler Carl** by Matt Dinniman right here at Dungeon Books - 115 Brunswick St, Storefront 1R, Jersey City. we're open wed-sun, 12-7pm. can't see inventory from here, so worth asking in the shop if u want it same day. ship it or picking up?
```

**glm-5.3-flash-flex** (2.0s, tools: get_doc) - over-capitalised

```
u can grab **Dungeon Crawler Carl** by Matt Dinniman right here at Dungeon Books - 115 Brunswick St, Storefront 1R, Jersey City. we're open wed-sun, 12-7pm. ship it or picking up?
```

**kimi-k2.6-fast** (1.4s, tools: none) - clean

```
u can grab it through us at Dungeon Books, or ask in the shop next time ur in Jersey City. we carry more than the site shows, so it's worth checking. if u want me to look up the book details or put u on a search link, just say the word.
```

**kimi-k2.6-fast** (2.0s, tools: get_doc) - clean

```
you can grab it from us at Dungeon Books, 115 Brunswick St, Storefront 1R in Jersey City. we're open wed-sun 12-7pm eastern. want me to check if we've got **Dungeon Crawler Carl** in stock, or i can pull up the book details for u.
```

**kimi-k2.7-code-fast** (7.1s, tools: get_doc, hardcover_api) - superlative(best)

```
best bet is the shop itself. Dungeon Books is at 115 Brunswick St, Storefront 1R, Jersey City, open Wed-Sun 12-7pm. we carry more than the site shows, so it's worth asking in person or giving us a call at (760) 364-6257.

**Dungeon Crawler Carl** by Matt Dinniman is litRPG where earth gets turned into a dungeon crawl game show, and the main guy's only companion is his ex-girlfriend's cat. it's funny, brutal, and way better than it has any right to be.
```

**kimi-k2.7-code-fast** (2.0s, tools: get_doc) - clean

```
Dungeon Books is at 115 Brunswick St, Storefront 1R in Jersey City. open Wed-Sun 12-7pm. call (760) 364-6257 or email hello@dungeonbooks.com to check if **Dungeon Crawler Carl** is in stock. we carry more than the site shows, so it's worth asking.
```

**kimi-k3-fast** (1.3s, tools: none) - clean

```
yo, you can grab **Dungeon Crawler Carl** by Matt Dinniman right here at dungeon books. we're in jersey city, open wed-sun 12-7pm. if you're not local, i can point you to our online store. want me to check if we have it in stock for you?
```

**kimi-k3-fast** (1.2s, tools: none) - clean

```
yo, you can grab **Dungeon Crawler Carl** by Matt Dinniman right here at Dungeon Books. we're in jersey city, open wed-sun 12-7pm. or if you want it shipped, check the site. it's that sci-fi/fantasy where earth gets turned into a dungeon and this dude carl has to survive with his cat princess donut. pretty solid.
```

### store_hours

> what time do you close on sunday

**glm-5.2-short** (2.4s, tools: get_doc) - clean

```
we close at 7pm on sundays. open noon to 7 wednesday through sunday, closed mondays and tuesdays.
```

**glm-5.2-short** (14.3s, tools: get_doc) - clean

```
we close at 7pm on sundays. open from noon.
```

**glm-5.3-flash** (1.6s, tools: get_doc) - clean

```
we close at 7pm on sunday. open 12-7 wednesday through sunday, closed mondays and tuesdays.
```

**glm-5.3-flash** (1.6s, tools: get_doc) - clean

```
we close at 7pm on sunday. open 12-7 wed through sun, closed mon/tues.
```

**glm-5.3-flash-flex** (89.6s, tools: get_doc) - clean

```
we close at 7pm on sunday. open 12-7 wed-sun.
```

**glm-5.3-flash-flex** (30.8s, tools: get_doc) - clean

```
we close at 7pm on sunday. open 12-7 wednesday through sunday, closed mondays and tuesdays.
```

**kimi-k2.6-fast** (4.9s, tools: get_doc) - clean

```
we close at 7pm on sundays. we're open wednesday-sunday, 12-7pm eastern.
```

**kimi-k2.6-fast** (2.7s, tools: get_doc) - clean

```
we close at 7pm on sunday. we're open wednesday through sunday, 12-7pm eastern.
```

**kimi-k2.7-code-fast** (2.0s, tools: get_doc) - clean

```
we close at 7pm on sunday. we're open wed-sun 12-7pm eastern, closed monday and tuesday.
```

**kimi-k2.7-code-fast** (2.1s, tools: get_doc) - clean

```
we close at 7pm on sunday. open 12-7 wed-sun.
```

**kimi-k3-fast** (2.0s, tools: get_doc) - clean

```
we're open wednesday to sunday, 12-7pm eastern. so we close at 7pm on sundays.
```

**kimi-k3-fast** (20.0s, tools: get_doc) - clean

```
we close at 7pm on sundays. open 12-7 wed through sun, closed mon and tue.
```

### why_read

> why should i read Dune

**glm-5.2-short** (1.4s, tools: none) - clean

```
bc it's the granddaddy of modern sci-fi and still holds up. ecology, religion, politics, and spice-fueled space feudalism all in one package - Herbert basically asked "what if a messiah was a deliberate political project" and never flinched from the answer.

also the worldbuilding is absurdly deep. arrakis feels like a real place, the fremet feel like a real people, and paul atreides is one of the great complicated protagonists. half the sci-fi you've read is downstream of this book.
```

**glm-5.2-short** (1.7s, tools: none) - clean

```
bc it's the blueprint. basically every sci-fi thing u love - star wars, warhammer 40k, arrakis in every space opera - is downstream of Herbert's desert planet.

it's also a political chess match disguised as an adventure story. ecology, religion, spice economics, prophecies people engineer centuries in advance. paul atreides isn't a chosen one, he's a guy who gets trapped in a myth other people built for him, and the book knows it.

it's dense but it earns it. if u want the lighter entry point, start with **Dune Messiah** after anyway, it's the "wait, hold on" sequel. but read **Dune** first, it's the foundation.
```

**glm-5.3-flash** (1.9s, tools: none) - clean

```
it's the blueprint for like half of modern sci-fi. politics, ecology, religion, and giant sand worms, all in one book. herbert wrote it in 1965 and people are still stealing from it - star wars owes it a debt, dune's influence is everywhere.

the fun part is it reads like a space opera on the surface but it's actually about the danger of messiahs and what resource empires do to people. spice = oil, basically, decades before that was a common sci-fi move.

also it's just fun. feuding noble houses, knife fights, a betrayal you'll see coming and still feel. if the length scares u, the first book stands alone fine.
```

**glm-5.3-flash** (1.4s, tools: none) - clean

```
short version: it's the book every big space opera since 1965 is measuring itself against. politics, ecology, religion, and giant sandworms, all at once - frank herbert did the "planets as characters" thing before anyone else.

also it holds up on rereads. first pass is the adventure, second pass you notice how much herbert buried about power and messiahs. good times.

if u want, i can pull up the details on it.
```

**glm-5.3-flash-flex** (39.4s, tools: none) - clean

```
Dune's worth it for a few reasons. it basically invented modern ecological sci-fi - the whole thing is about desert survival, religion, and power, and Herbert actually did the homework on all three. paul's arc is a deconstruction of the chosen-one story before that was a thing, so it reads way darker and smarter than people expect. also the worldbuilding still holds up 60 years later, good times were had writing it.

if u want space opera with actual ideas behind it, this is the one.
```

**glm-5.3-flash-flex** (3.4s, tools: none) - clean

```
Dune's the classic for a reason - it's epic sci-fi where ecology, religion, and politics all collide on a desert planet. Herbert built the whole thing around the idea that heroes are dangerous, which is a way better hook than it sounds. Plus giant sandworms, spice that extends life, and Paul's prescient visions. It holds up.
```

**kimi-k2.6-fast** (1.4s, tools: none) - clean

```
it's the ur-text for a lot of modern sci-fi.

**Dune** by Frank Herbert is basically feudal politics, ecology, and messiah complexes set on a desert planet where the most valuable substance in the universe is worm poop. the worldbuilding is absurdly deep and a lot of it still hits.

if u like big ideas, sand, and houses scheming against each other, it's worth it. fair warning: the prose is denser than a lot of current sci-fi.
```

**kimi-k2.6-fast** (1.5s, tools: none) - clean

```
try **Dune** by Frank Herbert if u want politics, ecology, and weird religion baked into one big desert opera. paul's arc is less chosen-one power fantasy than a tragedy about prophecy and empire, which is why it still hits after sixty years. the worldbuilding is dense but not decorative. every faction has a real ideological stake.

also the first book stands alone fine. stop there or keep going, no wrong move.
```

**kimi-k2.7-code-fast** (1.4s, tools: none) - clean

```
try **Dune** by Frank Herbert - it's the ur-text for a lot of modern sci-fi.

it's a desert-planet political epic about ecology, religion, empire, and what messiahs actually cost. the worldbuilding is dense but rewards patience, and the Bene Gesserit stuff still feels ahead of its time. if you like power games, weird ecology, and characters who think before they fight, it's worth the slow start.
```

**kimi-k2.7-code-fast** (43.6s, tools: hardcover_api, hardcover_api) - too-long(10>8)

```
**Dune** by Frank Herbert is the ur-text for a lot of modern sci-fi. desert planet, sandworms, space feudalism, a drug that lets you fold space. it reads like a political thriller wrapped in ecological worldbuilding.

what makes it stick is that Herbert isn't just worldbuilding for fun. he's dead serious about ecology, religion, colonialism, and what happens when a chosen one actually wins. paul atreides gets everything he wanted and it turns out to be a disaster. that's the whole book.

fair warning: the prose is dense and there's a glossary in the back for a reason. if you want something breezier, this ain't it. but if u want a book that invents half the tropes u see in modern sf, it's worth the climb.
```

**kimi-k3-fast** (1.2s, tools: none) - smart-punctuation('’')

```
yo. **Dune** by Frank Herbert is basically the blueprint for modern sci-fi. it’s got politics, ecology, religion, and giant worms all mashed into one dense story about a kid trying to survive on a desert planet. if you like worldbuilding that actually feels real and lived-in, it’s worth your time.
```

**kimi-k3-fast** (1.4s, tools: none) - smart-punctuation('’')

```
**Dune** by Frank Herbert is worth reading because it blends epic sci-fi worldbuilding with deep political intrigue and ecological themes that still resonate today. The story follows Paul Atreides as he navigates betrayal, prophecy, and survival on the desert planet Arrakis. It’s a dense but rewarding read, especially if you like complex characters and big ideas.
```

### comparison

> how does Gideon the Ninth compare to Locked Tomb sequels

**glm-5.2-short** (3.2s, tools: none) - clean

```
**Gideon the Ninth** is the most accessible of the bunch - it's basically a locked-room murder mystery with necromancers in space, and Gideon's snark carries the whole book. **Harrow the Ninth** flips everything: unreliable narrator, second person at times, and you spend half the book figuring out what's even happening. **Nona the Ninth** slows way down and gets weirdly tender. muir's writing gets more structurally ambitious as the series goes on, so if u liked Gideon's voice but want plot clarity, brace yourself. most people say Harrow is the peak but it demands rereading.
```

**glm-5.2-short** (1.9s, tools: none) - too-long(7>5)

```
**Gideon The Ninth** by Tamsyn Muir is the most accessible of the bunch. it's basically a locked-room murder mystery with necromancers and space, and gideon's voice carries it - snarky, horny, kind of an idiot. the sequels get weirder and more ambitious. Harrow shifts perspective and format hard, and Nona goes almost slice-of-life before things get heavy. some people bounce off the later books bc the plot gets genuinely confusing, but that's kind of the point. if u like gideon's humor, the payoff in the later books is worth the disorientation. start with gideon tho, don't skip around.
```

**glm-5.3-flash** (2.2s, tools: none) - too-long(9>5)

```
Gideon the Ninth is the most fun of the bunch - snarky lesbian necromancers in space, sword fights, a murder mystery in a haunted house. Tamsyn Muir's voice is doing most of the heavy lifting there.

The sequels get weirder and more demanding. Harrow the Ninth is a puzzle box - unreliable narration, second-person sections, and you spend a lot of it confused on purpose. Nona the Ninth is gentler and stranger, more character-focused, then the ending hits hard. Alecto is still coming.

General vibe: if u loved Gideon's humor, expect less of it upfront in Harrow. Worth pushing through though - rereads reveal a lot. i knew a necromancer once, less pleasant than Muir's.
```

**glm-5.3-flash** (1.5s, tools: none) - too-long(7>5)

```
Gideon the Ninth is the loudest of the bunch - swordswoman with a chip on her shoulder, snarky first-person voice, locked-room mystery in a haunted space mausoleum. the sequels shift gears hard: Harrow the Ninth is disorienting and grief-soaked, second person, unreliable everything. Nona the Ninth is gentler and stranger, following a sweet amnesiac in a dying city. Alecto wraps it all up and rewards rereads more than any of them.

honestly the sequels are better written but Gideon is the most fun. people bounce off Harrow's confusion-on-purpose style, so go in knowing that. if u liked Gideon's voice, Harrow will test u, then pay off.
```

**glm-5.3-flash-flex** (4.4s, tools: none) - too-long(8>5)

```
yo. **Gideon the Ninth** is the loudest of the bunch - sword fights, snark, Gideon's voice carrying everything. **Harrow the Ninth** is where Tamsyn Muir goes weird: second person, unreliable narration, way more grief. some people bounce off it, others think it's the peak.

**Nona the Ninth** is gentler and stranger, a slower character study with big questions underneath. then **Alecto the Ninth** wraps it up whenever it lands.

if u loved Gideon's humor, expect the sequels to keep the jokes but get darker and more labyrinthine. worth it if u like puzzles, tbh.
```

**glm-5.3-flash-flex** (1.8s, tools: none) - too-long(7>5)

```
yo. Gideon the Ninth is the loudest of the lot - sword fights, snark, necromancers in space. Harrow the Ninth flips perspective and gets way weirder and more psychological, Nona the Ninth is softer and stranger, and Alecto wraps it up. same universe, escalating mystery about what's actually going on with the Emperor and the resurrection.

if u liked the banter most, Gideon stays the peak. if u want the lore to snap into place, the sequels pay off hard. worth reading in order, they don't really stand alone.
```

**kimi-k2.6-fast** (1.9s, tools: none) - too-long(11>5)

```
**Gideon the Ninth** is the fun one: snarky, locked-house mystery in a crumbling space necropolis, Gideon's voice carries the whole thing.

**Harrow the Ninth** gets weird on purpose. second-person, fractured timeline, grief as architecture. people either love the puzzle or bounce off it hard.

**Nona the Ninth** slows way down, almost pastoral body-swap stuff with dogs and nuns, while the cosmology gets bigger in the background.

**Alecto the Ninth** wraps the timeline games and the god stuff. it's a lot.

if u liked Gideon's voice and the mystery, Harrow rewards patience but demands it. if u want the same tone, Nona and Alecto aren't really trying to repeat it. they're doing one long escalation.

u on book one now or somewhere in the sequels?
```

**kimi-k2.6-fast** (1.8s, tools: none) - too-long(9>5)

```
**Gideon the Ninth** is the snarky, sword-lesbian dungeon crawl entry point. it has a closed mystery structure, bone jokes, and a relatively contained cast.

the sequels scale way up. **Harrow the Ninth** goes full unreliable narrator and second-person grief spiral. it's structurally weirder and harder going in. **Nona the Ninth** shifts protagonists and gets more cosmic/religious, with a slower emotional burn. **Alecto the Ninth** is supposed to close it all out.

if you want fun action with mystery bones, Gideon is the easy sell. if you want to be emotionally dismantled by a puzzle box, keep reading.
```

**kimi-k2.7-code-fast** (2.1s, tools: none) - superlative(best), too-long(14>5)

```
**Gideon the Ninth** is the most straightforward: snarky sword lesbian gets dragged into a haunted space necromancer murder mystery. it's fun, propulsive, and Gideon's voice carries the whole thing.

**Harrow the Ninth** goes weirder. second-person sections, timeline fuckery, and it assumes you're paying close attention. some people bounce off it, others think it's the best one. it rewards a reread.

**Nona the Ninth** shifts protagonists and slows the pace down a lot. it's warmer and more grounded on one hand, and cosmic body horror on the other. if you want answers, it gives some but also opens bigger doors.

**Alecto the Ninth** wraps the series and goes full theology/empire/identity. it's dense.

if you liked Gideon's voice and want more of that, Harrow might frustrate you at first. if you want the world to get bigger and stranger, the sequels deliver. what'd you like most about Gideon?
```

**kimi-k2.7-code-fast** (2.4s, tools: none) - superlative(best), not-x-but-y, too-long(11>5)

```
**Gideon the Ninth** is the tightest and funniest of the bunch. it has a murder-mystery structure, snappy banter, and gideon's voice carrying the whole thing. it's basically "lesbian swordswoman insults necromancers in a haunted space palace."

**Harrow the Ninth** goes weirder and more formally experimental. it's doing a lot with unreliable narration and a second-person structure, and the plot twists hard late in the book. some people bounce off it, others think it's the best one.

**Nona the Ninth** shifts tone again. slower, more character-focused, almost slice-of-life at times, but it's building toward the bigger picture. if you want the gideon-voice energy back, it's not really there, but it pays off stuff harrow set up.

 sequels get more cosmically ambitious and more emotionally brutal. if you loved gideon for the voice and the mystery, harrow might feel like a curveball. if you're in it for the world and the long game, the sequels reward that.
```

**kimi-k3-fast** (1.4s, tools: none) - clean

```
**Gideon the Ninth** is basically a locked-room murder mystery in a haunted space castle with necromancer nuns. **Harrow the Ninth** gets way weirder and more experimental with the structure - unreliable narrator stuff, reality-bending. **Alecto the Ninth** isn't out yet but **Nona the Ninth** (the actual third book) goes full slice-of-life amnesia story. each one kinda reinvents what the series is doing. you read Gideon yet?
```

**kimi-k3-fast** (1.6s, tools: none) - too-long(6>5)

```
**Gideon the Ninth** is basically a locked-room murder mystery with necromancy and sword fights. the sequels blow the scope wide open. **Harrow the Ninth** gets weird with structure (second person, unreliable narrator stuff) and goes full space opera politics. **Nona** and **Alecto** keep expanding the world and the time-jumping. so if you liked Gideon for the mystery and the characters, the sequels are less puzzle-box and more sprawling cosmic drama. still got the humor and the fucked up necromancer lore, just different pacing.
```

### tier_list

> rank the Green Bone Saga books

**glm-5.2-short** (2.5s, tools: none) - too-long(8>5)

```
Green Bone Saga by Fonda Lee, ranked:

1. **Jade City** - the setup is flawless. kung fu godfather saga with jade instead of guns, and the kaul family drama hits immediately
2. **Jade War** - the middle book that actually escalates. the international politics open up the world in a big way
3. **Jade Legacy** - the time skips are divisive but the payoff is earned. still great, just a step below the first two

honestly it's a tight trilogy, the gap between 1 and 3 is small. if u like mob stories with magic, start at the beginning, it's very much one long story.
```

**glm-5.2-short** (2.7s, tools: none) - clean

```
**Jade City** > **Jade War** > **Jade Legacy**, but honestly they're all good. Jade City is the tightest - kung fu godfathers running a jade trade like an organized crime family, and the ending hits hard. Jade War widens the world and gets into international politics, some pacing dips but the payoff's there. Jade Legacy is the long one, covers decades, and people split on the ending but i think it sticks the landing. read in order, don't skip.
```

**glm-5.3-flash** (4.1s, tools: none) - too-long(13>5)

```
honest ranking:

1. **Jade City** - tightest of the three. family drama + kung fu + geopolitics in one clean package. sets up the Kauls perfectly.
2. **Jade Legacy** - the epic payoff. spans decades, big swings, emotional gut punches. a bit sprawling but earns it.
3. **Jade War** - still good, but the middle-book slog hits a little. more political maneuvering, less jade fighting.

tbh it's a rare trilogy where even the "worst" book is great. fonda kaul supremacy, that's my take.
```

**glm-5.3-flash** (1.1s, tools: none) - too-long(10>5)

```
easy, here's my take:

1. **Jade Legacy** - the finale goes big, decades-spanning, and sticks the landing. rare for a trilogy to end that well.
2. **Jade City** - tightest of the three, great setup, the Kaul siblings click right away.
3. **Jade War** - still good, but it widens the world and drags a little in the middle.

honestly the gaps are small. it's one of the better completed trilogies of the last decade. jade-wielding gangster families, god of war energy, worth the whole ride.
```

**glm-5.3-flash-flex** (3.6s, tools: none) - too-long(11>5)

```
easy one. Fonda Lee's Green Bone Saga:

1. **Jade Legacy** - the finale, biggest scope, pays off everything. some think it's the peak.
2. **Jade City** - tightest of the three, godfather-with-magic-jade in a kowloon-ish city. great starting point.
3. **Jade War** - middle book syndrome is real here but it expands the world (international politics, the drug trade) and sets up Legacy.

honestly the whole trilogy is a top-tier modern fantasy run. start with Jade City and thank me later.
```

**glm-5.3-flash-flex** (15.8s, tools: none) - too-long(12>5)

```
easy, that's a good series. my ranking:

1. **Jade City** - tightest of the three. family drama + kung fu + politics, and it does the godfather thing better than most godfather homages.
2. **Jade Legacy** - huge generational sweep, ends the saga properly. only third bc the middle drags in spots.
3. **Jade War** - still good, but it's the bridge book. sets up the international stuff that pays off later.

honestly the gaps are small. if u like one u'll read all three.
```

**kimi-k2.6-fast** (1.2s, tools: none) - too-long(7>5)

```
1. **Jade Legacy** - the trilogy capper, goes epic and pays off everything built across the first two.
2. **Jade City** - where it all starts, tight gangland family drama with magic kung fu.
3. **Jade War** - middle book syndrome a little, still good but mostly setup for the finale.

that's the order i'd reread them in too.
```

**kimi-k2.6-fast** (2.2s, tools: none) - superlative(best), too-long(12>5)

```
the **Green Bone Saga** by Fonda Lee is one of the best modern fantasy trilogies, period. it does godfather-style crime family drama in a secondary-world asian-inspired setting with jade-powered martial arts. if u like moral complexity, generational trauma, and people making terrible decisions for love of family, this hits.

my ranking:

1. **Jade War** - the middle book that somehow levels up everything. expands the world, deepens the clan conflict, and the ending still guts me.
2. **Jade Legacy** - huge, sprawling, generations pass, satisfying as hell but a shade less tight than book 2.
3. **Jade City** - still excellent, just the setup. necessary and great, but the saga gets better as it goes.

if u want i can grab details/ratings on any of them.
```

**kimi-k2.7-code-fast** (1.5s, tools: none) - smart-punctuation('—'), superlative(best), too-long(8>5)

```
my ranking:

1. **Jade War** — widens the world without losing the family drama, the best balance of scale and heart.
2. **Jade Legacy** — huge, satisfying, a little overstuffed but sticks the landing.
3. **Jade City** — solid setup, great premise, just hasn't hit full stride yet.

it's basically godfather with magic jade and kung fu gangs. if u haven't started, worth it.
```

**kimi-k2.7-code-fast** (1.7s, tools: none) - too-long(9>5)

```
solid trilogy. my ranking:

1. **Jade War** - widens the world beyond kaul sen to the international stage, raises the stakes without losing the family drama.
2. **Jade Legacy** - huge payoff, but it's doing a lot of cleanup and the scope almost buckles under its own weight.
3. **Jade City** - great setup and the clan politics hit hard, but it's mostly laying groundwork.

so basically: middle book, finale, opener. how would u rank em?
```

**kimi-k3-fast** (1.1s, tools: none) - clean

```
yo. for me it's **Jade War** at the top. it widens the world without losing the family core. then **Jade City** for the tight setup and that first big clan punch. **Jade Legacy** is still good, just a bit more sprawling and less sharp.
```

**kimi-k3-fast** (1.3s, tools: none) - clean

```
yo. for me it goes **Jade War** -> **Jade City** -> **Jade Legacy**.

war tightens the scope and the politics, city sets the hook, legacy is solid but sprawls a bit.
```

### mtg_card

> what does Lightning Bolt do

**glm-5.2-short** (3.9s, tools: scryfall_api) - clean

```
3 damage to any target for one red mana. the classic. been ending games since 1993 and it's still the benchmark for efficient removal.
```

**glm-5.2-short** (23.1s, tools: scryfall_api) - superlative(best)

```
3 damage to any target for one red mana. been ending games since 1993, still one of the best cards ever printed. classic.
```

**glm-5.3-flash** (2.7s, tools: scryfall_api) - clean

```
classic. **Lightning Bolt** is a red instant for one mana: it deals 3 damage to any target. creature, player, planeswalker, whatever. one of the most iconic cards ever printed.
```

**glm-5.3-flash** (3.5s, tools: scryfall_api) - clean

```
classic red instant, one red mana: **Lightning Bolt** deals 3 damage to any target. creature, player, planeswalker, whatever. one of the most iconic cards ever printed, honestly.
```

**glm-5.3-flash-flex** (65.1s, tools: scryfall_api) - clean

```
classic red instant. one red mana, deals 3 damage to any target - creature, player, planeswalker, whatever. been around since alpha, still one of the most efficient burn spells ever printed.
```

**glm-5.3-flash-flex** (17.7s, tools: scryfall_api) - superlative(best)

```
classic red instant, one red mana: **Lightning Bolt** deals 3 damage to any target - creature, player, planeswalker, whatever. simple and still one of the best burn spells ever printed. embed should be on screen with the card.
```

**kimi-k2.6-fast** (1.8s, tools: scryfall_api) - clean

```
one red mana instant. **Lightning Bolt** deals 3 damage to any target. that's a creature, planeswalker, or player.

simple, efficient, classic. good times.
```

**kimi-k2.6-fast** (1.6s, tools: scryfall_api) - clean

```
1 red mana instant. deals 3 damage to any target - creature, player, planeswalker, whatever. simple, efficient, classic.
```

**kimi-k2.7-code-fast** (1.4s, tools: scryfall_api) - clean

```
one red mana instant. deals 3 damage to any target - creature, player, planeswalker, whatever. simple, efficient, iconic.
```

**kimi-k2.7-code-fast** (1.9s, tools: scryfall_api) - clean

```
**Lightning Bolt** is a one-mana red instant that deals 3 damage to any target. that means creatures, planeswalkers, or players. it's been a red staple forever because 3 damage for {R} is an absurd rate.
```

**kimi-k3-fast** (0.8s, tools: none) - smart-punctuation('’')

```
Lightning Bolt deals 3 damage to any target. It’s a red instant that costs {R}.
```

**kimi-k3-fast** (1.2s, tools: none) - smart-punctuation('’')

```
Lightning Bolt deals 3 damage to any target. It’s a red instant for {R}, so you can zap a creature, planeswalker, battle, or player at instant speed.
```

### long_explain

> explain appendix n to me, i've never heard of it

**glm-5.2-short** (3.3s, tools: none) - clean

```
appendix n is the reading list gary gygax put at the back of the original 1979 dungeon masters guide - basically the books that inspired d&d. it's stuff like Robert E. Howard's conan stories, Fritz Leiber's fafhrd and gray mouser, Jack Vance (whose magic system is literally where d&d spell memorization comes from), plus weird ones like Poul Anderson and Roger Zelazny.

it's become a whole subgenre shorthand now - "appendix n" basically means old-school sword and sorcery and weird fantasy from the 30s-70s. honestly a lot of it holds up better than you'd think, and some of it is rougher than you'd think.

if u want a starting point, Leiber or Vance are the fun ones. i might be biased, i knew a few of these folks. want a rec or two?
```

**glm-5.2-short** (4.9s, tools: none) - too-long(11>8)

```
appendix n is the reading list at the back of the original 1979 dungeon masters guide for dnd. gary gygax listed the fiction that inspired the game - like 30ish authors, couple hundred books.

the vibe is mostly sword and sorcery and weird fiction: Robert E. Howard's conan stories, Fritz Leiber's Fafhrd and the Gray Mouser, Jack Vance's dying earth (that's where dnd's magic system comes from, the whole "memorize spells and they vanish when cast" thing is straight vance), Michael Moorcock's elric, H.P. Lovecraft, Clark Ashton Smith, plus some deeper cuts like Poul Anderson and L. Sprague de Camp.

it matters bc it's basically the dna of dnd and everything it spawned. a lot of people use it as a reading list now - there's even a whole publishing scene reprinting the obscure stuff. anderson's **Three Hearts and Three Lions** is on there btw, i'm partial to that one.

want some recs from the list? we carry a lot of it.
```

**glm-5.3-flash** (1.5s, tools: none) - clean

```
appendix n is the reading list at the back of the original Dungeon Masters Guide from 1979 - Gary Gygax's list of books and authors that inspired D&D. burroughs, howard, anderson, lovecraft, leiber, vance, that crowd. it's basically the source code for old-school fantasy, and half of it holds up really well. good times. if u want a starting point, **The Dying Earth** by Jack Vance or **Conan** stories by Robert E. Howard are the classics.
```

**glm-5.3-flash** (2.3s, tools: none) - too-long(11>8)

```
appendix n is the list of "inspirational and educational reading" in the back of the original 1979 Dungeon Master's Guide. gary gygax basically dumped his favorite pulp fantasy/sci-fi authors in there - robert e. howard, h.p. lovecraft, fritz leiber, jack vance, poul anderson, edgar rice burroughs, a. merritt, michael moorcock, etc.

it matters bc it's basically the dna of d&d. vance's magic gave us vancian spell slots, howard's conan gave us the sword-and-sorcery vibe, and the whole "adventurer loots a dungeon" thing comes straight from those pulps. a lot of those books are public domain or cheap reprints now, so it's a great reading list if u want to know where the game came from.

we keep a bunch of appendix n authors on the shelf - ask next time ur in the shop. good times, that era. i knew a couple of those guys actually.
```

**glm-5.3-flash-flex** (61.8s, tools: none) - too-long(10>8)

```
appendix n is the reading list at the back of the original Dungeon Masters Guide (1979). gary gygax listed the books that shaped d&d - robert e. howard, h.p. lovecraft, jack vance, fritz leiber, poul anderson, that crowd.

it matters bc it's basically the dna of d&d. vance's magic system (spells vanish from memory after casting) became the vancian spell slots everyone uses. howard's sword-and-sorcery gave us the barbarian. it's the reason d&d feels like pulpy 60s-70s fantasy instead of tolkien.

worth reading if u want to know where the game came from. a lot of it holds up tbh.
```

**glm-5.3-flash-flex** (3.8s, tools: none) - clean

```
appendix n is the list of inspirational reading in the back of the original 1977 Dungeon Masters Guide. gary gygax basically listed the books that shaped d&d - stuff like Burroughs' Barsoom books, Lovecraft, Howard's Conan tales, Vance's Dying Earth, Moorcock, Anderson's Three Hearts and Three Lions (good times, that one).

it's become shorthand for that whole mid-century pulp fantasy/sf tradition: sword & sorcery, planetary romance, weird fiction. a lot of modern "osr" games cite it directly as their creative lineage. if u want a starting point, **The Dying Earth** by Jack Vance is short, funny, and the source of basically all d&d magic.
```

**kimi-k2.6-fast** (1.8s, tools: none) - clean

```
appendix n is the reading list in the back of the original advanced dungeons & dragons dungeon masters guide (1979). gary gygax listed the fantasy and sci-fi books that inspired d&d.

it's the canon: robert e. howard's conan, jack vance's dying earth, michael moorcock's elric, fritz leiber's fafhrd and the gray mouser, h.p. lovecraft, lord dunsany, and a bunch more.

if u want a place to start, try **The Dying Earth** by Jack Vance. that's where the whole "fire-and-forget" magic system came from.
```

**kimi-k2.6-fast** (2.2s, tools: none) - italics

```
appendix n is the reading list at the back of the original 1979 *Dungeon Masters Guide* by Gary Gygax. it's the stuff that inspired early D&D - fantasy, sci-fi, horror, and pulp.

think robert e. howard's **Conan**, michael moorcock's **Elric**, jack vance's **Dying Earth**, h.p. lovecraft, lord dunsany, fritz leiber's **Fafhrd and the Gray Mouser**. it also pulls in sci-fi like poul anderson and andre norton.

it's basically a map to where D&D came from. if u want the classic sword-and-sorcery vibe, that's the list.
```

**kimi-k2.7-code-fast** (1.9s, tools: none) - italics

```
appendix n is the reading list at the back of the first edition *Dungeon Masters Guide* by Gary Gygall. he put it there to show dungeon masters what books inspired D&D.

it's a mix of pulp fantasy, sci-fi, horror, and historical adventure. think **The Hobbit**, **Conan**, **Fafhrd and the Gray Mouser**, **Dying Earth**, **Three Hearts and Three Lions** (where i happen to live), plus H.P. Lovecraft, A. Merritt, and even some non-fiction like *The Golden Bough*.

it's basically the DNA of old-school D&D. if u want the vibe of early D&D, read those books.
```

**kimi-k2.7-code-fast** (1.9s, tools: none) - italics

```
appendix n is the reading list at the back of the original 1979 *dungeon masters guide* by gary gygax. it's basically the family tree of d&d.

it lists the books, authors, and stories gary and the early tsr crew were pulling from when they built the game. we're talking **robert e. howard's conan**, **fritz leiber's fafhrd and the gray mouser**, **michael moorcock's elric**, **jack vance's dying earth**, **h.p. lovecraft**, **poul anderson**, **lord dunsany**, and a bunch more.

if u like d&d and want to know why the game feels the way it does, appendix n is the cheat sheet. a lot of modern fantasy fans trace their whole tbr back to that page.
```

**kimi-k3-fast** (1.6s, tools: none) - clean

```
Appendix N is a list of recommended reading from the 1979 Dungeon Master's Guide, written by Gary Gygax. It names the fantasy and sci-fi authors who shaped early D&D - people like Robert E. Howard, Fritz Leiber, Jack Vance, Poul Anderson, Michael Moorcock, plus Tolkien and Lovecraft.

It matters because it's basically the DNA of the genre. Vancian magic (spells memorized then forgotten after casting), alignment, paladins, a lot of that comes straight from these books. Poul Anderson's Three Hearts and Three Lions is on there. Good book, obviously.

If you want to dive in, **The Dying Earth** by Jack Vance or **Fafhrd and the Gray Mouser** stories by Fritz Leiber are good starting points.
```

**kimi-k3-fast** (2.3s, tools: none) - clean

```
appendix n is the list of fantasy and sci-fi books that inspired dungeons & dragons. gary gygax included it in the 1979 dungeon masters guide as a "here's what shaped this game" reading list. it's basically the dna of modern fantasy - stuff like **The Lord of the Rings** by J.R.R. Tolkien, **Conan the Barbarian** by Robert E. Howard, **The Dying Earth** by Jack Vance, and **Three Hearts and Three Lions** by Poul Anderson (which is where i'm from, actually).

it's less a canon and more a vibe - pulp adventure, weird magic, morally gray heroes, that kind of thing. if you've ever wondered why d&d has vancian magic or where the whole "thieves' guild" trope came from, appendix n is ur answer.
```


## Findings

Neuralwatt lists no `glm-5.3-short` and no plain `kimi-k2.7`, only the
`kimi-k2.7-code` variants. `kimi-k2.6-fast` (production until this run) and
`glm-5.2-short` are unlisted but still answered every prompt.

`glm-5.3-flash` ties `glm-5.2-short` on violations with a much shorter tail
(p90 4.3s against 13.8s) and costs about a ninth of `kimi-k2.6-fast` per reply.
Nine of its eleven violations are replies over the sentence cap, which is a
prompt problem rather than a model one. It becomes the default.

`kimi-k3-fast` is marginally cleaner but 18x flash's cost and the only model
using smart punctuation. `glm-5.3-flash-flex` is a slow queue tier (24s median,
90s p90) and unusable for chat. `kimi-k2.7-code-fast` scored worst.

Every model answered "where can i buy Dungeon Crawler Carl" with the real store
address, and the phone number and email the Kimi models gave match
`policies/store.md`. The invented-address problem from the 2026-07-26 run did
not recur.
