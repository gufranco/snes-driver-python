# Cartridges

Nothing in this directory is shared. A cartridge belongs to whoever made it, and
no part of one is carried by this repository, published in the manifest, or
reconstructible from anything here. What the manifest holds is a name, a length
and four digests, and a digest reconstructs nothing.

Put copies you already own here and the reader runs against them. Leave the
directory empty and the checks that need one report as skipped rather than as
passed, so a run that proved nothing never reads as a run that proved something.

## Why a cartridge is the input rather than a fixture

This package reads the routine inside a cartridge that drives its coprocessor.
That routine is the only place the part's protocol is written down: most of these
parts have no surviving datasheet, and the emulators that talk to them were
written by people who read the same code.

So a file that is not the one named would be disassembled anyway and would report
a protocol nobody's hardware has. That is worse than reporting nothing, which is
why every cartridge is confirmed against four digests before a byte of it is read.

## Where they go

Here, keeping the filenames below, or anywhere `SNES_CARTRIDGE_DIR` points.
Subdirectories are walked. A named directory wins even when it turns out to be
empty, because quietly falling back from a path somebody typed turns a typo into a
run that reports nothing needed doing.

## What is checked

`sha256` decides. The other three are confirmed too rather than published and
ignored: a file can be the right length under the right name and still be a bad
dump, and a manifest that publishes a crc32 and never looks at it is publishing
decoration.

Check a copy before supplying it:

```bash
shasum -a 256 "Pilotwings (USA).sfc"
```

## The 42 cartridges

| File | Layout | Chipset | Bytes |
|------|--------|---------|------:|
| `3-jigen Kakutou Ballz (Japan).sfc` | hirom | 0x03 | 1048576 |
| `Ace o Nerae! (Japan).sfc` | hirom | 0x03 | 1048576 |
| `Ballz 3D - Fighting at Its Ballziest (USA).sfc` | hirom | 0x03 | 1048576 |
| `Battle Racers (Japan).sfc` | hirom | 0x05 | 1048576 |
| `Bike Daisuki! Hashiriya Tamashii (Japan).sfc` | hirom | 0x05 | 524288 |
| `Campus Challenge '92 - Pilotwings (USA).sfc` | lorom | 0x03 | 524288 |
| `Drift King Shutokou Battle '94 - Tsuchiya Keiichi & Bandou Masaaki (Japan).sfc` | hirom | 0x05 | 1572864 |
| `Drift King Shutokou Battle 2 - Tsuchiya Keiichi & Bandou Masaaki (Japan).sfc` | hirom | 0x05 | 1572864 |
| `Dungeon Master (Europe).sfc` | lorom | 0x05 | 1048576 |
| `Dungeon Master (Japan) (Rev 1).sfc` | lorom | 0x05 | 1048576 |
| `Dungeon Master (USA).sfc` | lorom | 0x05 | 1048576 |
| `Exhaust Heat II - F1 Driver e no Michi (Japan).sfc` | lorom | 0xf6 | 1048576 |
| `F1-ROC II - Race of Champions (USA).sfc` | lorom | 0xf6 | 1048576 |
| `Final Stretch (Japan).sfc` | hirom | 0x05 | 1572864 |
| `Hanguk Pro Yagu (Korea).sfc` | lorom | 0x05 | 1572864 |
| `Hayazashi Nidan Morita Shougi (Japan).sfc` | lorom | 0xf6 | 524288 |
| `Hayazashi Nidan Morita Shougi 2 (Japan).sfc` | lorom | 0xf5 | 524288 |
| `Lock On (USA).sfc` | hirom | 0x03 | 524288 |
| `Metal Combat - Falcon's Revenge (Europe).sfc` | lorom | 0x25 | 2097152 |
| `Metal Combat - Falcon's Revenge (USA).sfc` | lorom | 0x25 | 2097152 |
| `Michael Andretti's Indy Car Challenge (Japan).sfc` | hirom | 0x03 | 1048576 |
| `Michael Andretti's Indy Car Challenge (USA).sfc` | hirom | 0x03 | 1048576 |
| `Pilotwings (Europe).sfc` | lorom | 0x03 | 524288 |
| `Pilotwings (Japan).sfc` | lorom | 0x03 | 524288 |
| `Pilotwings (USA).sfc` | lorom | 0x03 | 524288 |
| `Planet's Champ TG 3000, The (Japan).sfc` | lorom | 0x03 | 1048576 |
| `PowerFest 94 - Super Mario Kart (USA).sfc` | hirom | 0x05 | 524288 |
| `SD Gundam GX (Japan).sfc` | lorom | 0x05 | 1048576 |
| `Soukou Kihei Votoms - The Battling Road (Japan).sfc` | hirom | 0x03 | 1048576 |
| `Super 3D Baseball (Japan).sfc` | lorom | 0x05 | 1572864 |
| `Super Air Diver (Europe).sfc` | hirom | 0x03 | 524288 |
| `Super Air Diver (Japan).sfc` | hirom | 0x03 | 524288 |
| `Super Air Diver 2 (Japan) (En).sfc` | hirom | 0x03 | 1310720 |
| `Super Bases Loaded 2 (USA).sfc` | lorom | 0x05 | 1572864 |
| `Super F1 Circus Gaiden (Japan).sfc` | hirom | 0x05 | 1310720 |
| `Super Mario Kart (Europe).sfc` | hirom | 0x05 | 524288 |
| `Super Mario Kart (Japan).sfc` | hirom | 0x05 | 524288 |
| `Super Mario Kart (USA).sfc` | hirom | 0x05 | 524288 |
| `Suzuka 8 Hours (Japan) (En).sfc` | hirom | 0x05 | 1048576 |
| `Suzuka 8 Hours (USA).sfc` | hirom | 0x03 | 1048576 |
| `Top Gear 3000 (Europe).sfc` | lorom | 0x03 | 1048576 |
| `Top Gear 3000 (USA).sfc` | lorom | 0x03 | 1048576 |

## Digests

| File | crc32 | md5 |
|------|-------|-----|
| `3-jigen Kakutou Ballz (Japan).sfc` | `f0810694` | `5403a00958bcb9a3d3fd714c48115e7e` |
| `Ace o Nerae! (Japan).sfc` | `6c5f1a18` | `572cf198450d3424da503f93d4e6ac85` |
| `Ballz 3D - Fighting at Its Ballziest (USA).sfc` | `1c058b7d` | `b61efd28676ea1f9ca650888753df2dc` |
| `Battle Racers (Japan).sfc` | `64b76ceb` | `3e49ef28a461a06435ae04c2e5341f78` |
| `Bike Daisuki! Hashiriya Tamashii (Japan).sfc` | `b363fc99` | `9bc21069d1c9eba86dad2ba0e994e5a1` |
| `Campus Challenge '92 - Pilotwings (USA).sfc` | `9bfe8684` | `775e305dd379a11a22a9035563b10a8b` |
| `Drift King Shutokou Battle '94 - Tsuchiya Keiichi & Bandou Masaaki (Japan).sfc` | `33ce298f` | `4a5a8a88353aeecd55fb6c13204d5882` |
| `Drift King Shutokou Battle 2 - Tsuchiya Keiichi & Bandou Masaaki (Japan).sfc` | `87aab79a` | `465f3757655a06741f7e2a7277ac4fca` |
| `Dungeon Master (Europe).sfc` | `89a67adf` | `1036e94c19d336069adde20d5a2ff15f` |
| `Dungeon Master (Japan) (Rev 1).sfc` | `aa79fa33` | `19d50794ff397278e11dbf3fbef58a58` |
| `Dungeon Master (USA).sfc` | `0dfd9ceb` | `3d1b171d7486438af2d9ec3d98b155cd` |
| `Exhaust Heat II - F1 Driver e no Michi (Japan).sfc` | `e2c8e535` | `9b0dffe0222a9b7b7c8dcb98cc8ca058` |
| `F1-ROC II - Race of Champions (USA).sfc` | `3447609e` | `000ba16a5a4c08992ec93d0309d8ed6c` |
| `Final Stretch (Japan).sfc` | `8d29f41f` | `750c39bc838483b569976cffadfbc7b6` |
| `Hanguk Pro Yagu (Korea).sfc` | `a21fb1d5` | `920d26154da3da96820ad07a3a05844a` |
| `Hayazashi Nidan Morita Shougi (Japan).sfc` | `81e822ad` | `ea342f4da33bf6eb3dc1fd2f89aa751f` |
| `Hayazashi Nidan Morita Shougi 2 (Japan).sfc` | `dd852671` | `5851671aea79961658d0e7b0ba99fc8b` |
| `Lock On (USA).sfc` | `84f7e078` | `76a5cf0ba713446cbec55d072e20528b` |
| `Metal Combat - Falcon's Revenge (Europe).sfc` | `eb0039c4` | `44a7735d6dceed9fb4eab61113daa410` |
| `Metal Combat - Falcon's Revenge (USA).sfc` | `c3131b49` | `d4bc4f3cb46cc09d8db58f0ce0142646` |
| `Michael Andretti's Indy Car Challenge (Japan).sfc` | `1128572b` | `2484f41a03392dee2116afb9c7d7bdc6` |
| `Michael Andretti's Indy Car Challenge (USA).sfc` | `0fdb210e` | `8874a87e4e0ccfa742e244017b6c544c` |
| `Pilotwings (Europe).sfc` | `def45776` | `b1e59f8246f1ab07670e5f1015189b3a` |
| `Pilotwings (Japan).sfc` | `77871727` | `55b2db1758dcfb0582ccafe6b0a763ec` |
| `Pilotwings (USA).sfc` | `266c44ed` | `8dcb216beed58c798b25df55f62218d0` |
| `Planet's Champ TG 3000, The (Japan).sfc` | `b9b9df06` | `6ae194d9f8022c9a2962a423ffbc40cc` |
| `PowerFest 94 - Super Mario Kart (USA).sfc` | `9974b593` | `2e8dc55d0241f01b2265dc6667932b9e` |
| `SD Gundam GX (Japan).sfc` | `4dc3d903` | `3c9e14d90815bfc9fd154a30c85763cf` |
| `Soukou Kihei Votoms - The Battling Road (Japan).sfc` | `c00f0bc9` | `026143f279d0936ce1372214450056a9` |
| `Super 3D Baseball (Japan).sfc` | `304123c2` | `ab42576ac7efb809f701a6c08f1554f3` |
| `Super Air Diver (Europe).sfc` | `0b57c764` | `cfb45d39478ac7af79276b047de3aa87` |
| `Super Air Diver (Japan).sfc` | `971e74ba` | `15ad304a4884722502ec2bb062d2cf56` |
| `Super Air Diver 2 (Japan) (En).sfc` | `a6ad6b0f` | `83e721806dd5ffae336e8caf03c2fc11` |
| `Super Bases Loaded 2 (USA).sfc` | `e14128ca` | `76951ba56bd1311b7a3bb3481a1a7920` |
| `Super F1 Circus Gaiden (Japan).sfc` | `6b8ac3b3` | `aac1685a925cd0a5a6819c6fde8e4531` |
| `Super Mario Kart (Europe).sfc` | `56410e5e` | `f9fe266e91632e68b558d6b43393eaba` |
| `Super Mario Kart (Japan).sfc` | `c8002453` | `f7afa112d7ec1d532636703e4b02700a` |
| `Super Mario Kart (USA).sfc` | `cd80db86` | `7f25ce5a283d902694c52fb1152fa61a` |
| `Suzuka 8 Hours (Japan) (En).sfc` | `b846b00d` | `81cee1957fa875efbedaff130848ba9e` |
| `Suzuka 8 Hours (USA).sfc` | `54740b9b` | `9f749083058a08a63cc026542dc3a904` |
| `Top Gear 3000 (Europe).sfc` | `493fdb13` | `462e15c018c653335ba634d3c1cd06c9` |
| `Top Gear 3000 (USA).sfc` | `a20be998` | `23eaa07e3f3315fa43f4b4d94ec97a7b` |

| File | sha1 | sha256 |
|------|------|--------|
| `3-jigen Kakutou Ballz (Japan).sfc` | `0caca71401b96b3ab42ec89e9bcf7af82b1bd3d4` | `1b59feccf5df19265b1885ea8e0ae85693a19650de338e898f4999f639695402` |
| `Ace o Nerae! (Japan).sfc` | `065bf1bbf4662383e2e42105ad76e0ed93213a57` | `9c9373e2a078ae47469d835fb4750ad0e4a46156c73baf573d3fabd132f5c184` |
| `Ballz 3D - Fighting at Its Ballziest (USA).sfc` | `236a466af4e05061b06d48bae637bb29f86672ad` | `e25d052d25264a14c4904aebc383482577bb5d2bb135f3ece88b1b7b0456a6bc` |
| `Battle Racers (Japan).sfc` | `02f3a5b09490987848e4b882122b19ff430ec7d7` | `ac9233fb2cf241e3c540d29c5d34ae5c4a821b09d86ccf2015a586edc7842096` |
| `Bike Daisuki! Hashiriya Tamashii (Japan).sfc` | `d0457fc27adff1b0ad236535f60f91711b15f0db` | `3fb25a3b30e897455de88e9e1d5ff2df81e56b89f3fe7b7d9e0248a19a146b4b` |
| `Campus Challenge '92 - Pilotwings (USA).sfc` | `76536914d2b058259f2297f76eaaafed7bb71e56` | `82571a02ac565e079ea269c0d8efc253a1dd68146ee54029f8aeaa751d073772` |
| `Drift King Shutokou Battle '94 - Tsuchiya Keiichi & Bandou Masaaki (Japan).sfc` | `719599ce4acbc1b790cb09506183bc2a9121671f` | `f6010bbaaad08c3427fa0273461399da15fb56a69be2144beeb688cbcddfe25d` |
| `Drift King Shutokou Battle 2 - Tsuchiya Keiichi & Bandou Masaaki (Japan).sfc` | `8d510935b6bf3a1ac42ef3501dca3477cc4cab5c` | `9fdd65a2921d9e2261734d764fcd87987c49b651c06adf60f6e5a9c754c2b7ca` |
| `Dungeon Master (Europe).sfc` | `30fc660fb1e78d0533f424da750112dcd615050a` | `e68eaed4eae2b1236264c0307b14bb2872e57471a166294e96ae56b7ba1a5e57` |
| `Dungeon Master (Japan) (Rev 1).sfc` | `e6d33ef74366333999ea11495c7a62d4ba07df0f` | `35ff99319ecc7ce1216c5096f46fcc11659254d570614d683f0f8ef773ed75b8` |
| `Dungeon Master (USA).sfc` | `e65ae62ec9a1c48a3512db66f929c7b0055ae2c3` | `2dfc2e037679a62a960dab9682bca6d1b2737f603edd336c8b2fdf05db10cc07` |
| `Exhaust Heat II - F1 Driver e no Michi (Japan).sfc` | `3600f81d5a7e2ec41f362cc22a16a58ce2612048` | `1c78d8208a05cbfe88ee019edbc3a0c9cdabfd2b62089ca119215bbc7e581611` |
| `F1-ROC II - Race of Champions (USA).sfc` | `fb81dd15b8a9ddf8f5564d3d2fb934c6f8bfb392` | `405c33f64701faf40963a4e6a2d0d69420e6751caf436387ddd3e145b25ed46c` |
| `Final Stretch (Japan).sfc` | `3c8e37271d995d9507d733864ab79b43ab531e96` | `4e22d625595dac0cf3c3053d9e715dc227d3bbe24adad826d5b3f2a035553617` |
| `Hanguk Pro Yagu (Korea).sfc` | `1e6b3ebdb5227626f4226ff9eef166294ffe063c` | `ce770d366ef5d956c865b803f98775f19f0c3b1e996f4499ef665bcaf697c47d` |
| `Hayazashi Nidan Morita Shougi (Japan).sfc` | `82b4bca58918a18707f932ec6afc0a12a3c4b872` | `85825a75ef662b28d0111c0462ec3c34234da1d78d10472b8022fcba3b9eaed5` |
| `Hayazashi Nidan Morita Shougi 2 (Japan).sfc` | `b291ada870b9ec09326cd2f9470ea1519cbaa2e9` | `40cec32f4c1b5a2564b8bb2e825ca1314d2171edb8e934956a74827e14bc9972` |
| `Lock On (USA).sfc` | `1f5e53a0391a902de6ee9407ed10803c84e23cc3` | `7e1d6242ae2ec2c23afb876becdcf778098edd4d853234222dc16471cb51df9e` |
| `Metal Combat - Falcon's Revenge (Europe).sfc` | `1d92ec65457c4e1bb984162412f2530cbaf13156` | `10d86e4f79d7bf966228067d963a5d2a40e0bddd79885436e3d18e24a2762e95` |
| `Metal Combat - Falcon's Revenge (USA).sfc` | `da88fc5830ddb0cdf8ffc2e8340a607d0ad8eaa1` | `d4f2cb6b209db29f7aec62e5a23846681c14665fb007e94d7bcfc7b5611e938b` |
| `Michael Andretti's Indy Car Challenge (Japan).sfc` | `ec07f7e81f13193805c3cd4b486118d218653da3` | `126081caccc4bac5d616608c20a3adec9cd50e8f2133824e693921160e835725` |
| `Michael Andretti's Indy Car Challenge (USA).sfc` | `20b7fd6a8604fa36f75edf9ccb24380b13d8c905` | `d3180e4c20b12e78e7a94a40d1f168d5a8198b21df9586ade0512720b415f67e` |
| `Pilotwings (Europe).sfc` | `d450d6d580d163fdfcc4f58d5bf8fafd7f510750` | `f70a72f3d3a65497cdc4d849877a29cf4f7bd10439bb7f5cb8675cdfc0e706d4` |
| `Pilotwings (Japan).sfc` | `76832034269723dc0aa7b9019faa5e8f39181e9d` | `d1845de22c3c7f2606bda20e09c8f7a78f92f5cbbb6bfe01f96a1d1e84b30394` |
| `Pilotwings (USA).sfc` | `fe941ba251acf329f028a1603a43562db2c75e51` | `03d0127f5de3237e22ad00de0c20763274da7b71142dde693240ac96d10983a3` |
| `Planet's Champ TG 3000, The (Japan).sfc` | `3e7f10e13065424a28c93871b4a1e458817d754c` | `7611e662666a33a9fca7569f26f85faeb687470b0d64ae853de411c0885000f7` |
| `PowerFest 94 - Super Mario Kart (USA).sfc` | `1c53c806d0dd5bad4b8b9337c0051ddaa0d3355f` | `19eb77affbf8dd068f5d79a3cf80a2084fd73237cd1ae4e47192b4422449e64a` |
| `SD Gundam GX (Japan).sfc` | `a504b74d1e256f97bc05a7dd836a2457ae6f525e` | `0cfea1ceee12d8276fedaf08f64e9413dccbd71ab83ae404b10276b893d46f6d` |
| `Soukou Kihei Votoms - The Battling Road (Japan).sfc` | `bf1f8c6abb074dc70b36cb2504a232e2e045bf34` | `a0347898ee96b7729ad5781e0784ad2a34469dfdc6755a7c6957501e26398729` |
| `Super 3D Baseball (Japan).sfc` | `124ee1ee5bae9268095037abd7d51045de6ac55e` | `0b6835fd11307d5e4adb8a8fc5e84fbbddeef8becddcceab65418da0618cf3f1` |
| `Super Air Diver (Europe).sfc` | `f70567b9dc858bdb66d73d539390b7f74f00ff8a` | `dc00b557e85b5f30e2a8cc269e12e55f71802c3024a6f8e9b299f0722a6f4a55` |
| `Super Air Diver (Japan).sfc` | `ffb81b82ea027673cbfc26f6ebd9f05c2d60d6c8` | `abec092d53fa56dd97b72279fcbe1545762d874daf721c4f3a1f3402da643d9c` |
| `Super Air Diver 2 (Japan) (En).sfc` | `acaec55441b7d894d33540d905e47e5fb0dacbcc` | `e0a648561c54c6f44819dfd88d27590a15686a0fc5bb3a67aed94d99323a7c11` |
| `Super Bases Loaded 2 (USA).sfc` | `d7d29e9a6a4820f2df03eeb80fdbc2b7df37f481` | `ff75fd4b096d48ce4a677c3321266d67077d6c586c9ee6926c7716a34f6d5ce1` |
| `Super F1 Circus Gaiden (Japan).sfc` | `a4179b57cec282cee174432dac651b1df9b6eacc` | `15a396dcc56cb40dc80733870d2d019cb59b80002ed05e746e4834ac07e22f13` |
| `Super Mario Kart (Europe).sfc` | `27d9b4f30d39af75075691344b7bdeedbd32ac19` | `1bdf422695a30e704e8abb7743b9c178d1ef2b200515a83cd41daef85e6b99e2` |
| `Super Mario Kart (Japan).sfc` | `cbb853bf911255c1d8eb27cd34fc7855a0dda218` | `c04f517c2675d7a8f3498d958f097443dfaa0e66606c69c59b58a915b3454973` |
| `Super Mario Kart (USA).sfc` | `47e103d8398cf5b7cbb42b95df3a3c270691163b` | `2ada8919688087be60a6a48cace8f877add60c45d2e5d09e2442faa55be62a49` |
| `Suzuka 8 Hours (Japan) (En).sfc` | `d110e337a49f6a635236c9bf485759e48411cb69` | `3aef80a3997b500a71ae76ac170c49b04f44dd8d9b60c0141d8aca0bb30567ac` |
| `Suzuka 8 Hours (USA).sfc` | `90a418a1d0a65c32ea8945c6496602f0d11514a5` | `ed8fa0dd7bb99957304e2de37f7dd79769d6534f9b01e290332b862f8ab43c4e` |
| `Top Gear 3000 (Europe).sfc` | `777d8732023a300a2c566f2d48bc354e0aa1da7e` | `4d7c81b0bad57a4c1c410fae4e58cd95fe25c29d7fb922778530cd457b5502e7` |
| `Top Gear 3000 (USA).sfc` | `058aadf1ee719cb9e0c7333e665797f990a6381d` | `6be49983976564f1fd9eff2f14f5bb41d3a0ff48573e39318088ecce286aca62` |

## The law this rests on

A length and a digest are measurements of a file rather than expression, and
measurements sit outside what copyright reaches under 17 U.S.C. 102(b) and Feist
Publications v. Rural Telephone Service. Reading a routine to learn how a part is
driven is the kind of examination Sega v. Accolade and Sony v. Connectix hold to be
fair. None of that extends to the cartridge itself, which is why it is not here.

