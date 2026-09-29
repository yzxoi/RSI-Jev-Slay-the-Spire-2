//! Offline lookup and synthetic mechanics audit of pinned upstream; not a game adapter.
use std::io::{self, BufRead};
use sts2core::{content, ops, replay, solver, state, Action, State, step};

fn synthetic() {
    let mut s = State::new(80, 1);
    s.add_enemy(content::enemy::UNKNOWN, 100);
    s.potions[0] = state::potion::BLOCK;
    let mut t = solver::Threat::new();
    t.set(0, 12, 1);
    let (dry, advice) = solver::advise_potions(&s, &t, solver::score::survive_first,
        10_000, &solver::PotionPolicy::HOUSE_RULE);
    assert_eq!(advice[0].verdict, solver::PotionVerdict::Drink);
    assert_eq!(advice[0].hp_saved, 12);
    let drank = step(s, Action::UsePotion { slot: 0, target: 0 });
    assert_eq!(drank.player.block, 12);
    assert_eq!(drank.potions[0], state::potion::NONE);
    assert!(dry.line.acts().iter().all(|a| !matches!(a, Action::UsePotion { .. })));
    println!("synthetic\tblock_12_incoming\tDrink\thp_saved=12; consumed_slot=true");

    s.potions[0] = state::potion::DEXTERITY;
    let (_, adv) = solver::advise_potions(&s, &t, solver::score::survive_first,
        10_000, &solver::PotionPolicy::HOUSE_RULE);
    assert_eq!(adv[0].verdict, solver::PotionVerdict::CrossTurn);
    assert_eq!(step(s, Action::UsePotion { slot: 0, target: 0 }).player.get(state::St::Dexterity), 2);
    println!("synthetic\tdexterity\tCrossTurn\trules_apply_dexterity=2");

    s.potions[0] = state::potion::BLOCK;
    let mut rec = Some(Vec::new());
    sts2core::rollout::solver_play_turn_rec(&mut s, 10_000, solver::score::survive_first, &mut rec);
    assert_eq!(s.potions[0], state::potion::BLOCK);
    println!("synthetic\trollout_policy\tno_potion\theld_block_potion=true");
    assert_eq!(replay::map_potion("BLOOD_POTION"), state::potion::UNKNOWN);
    println!("synthetic\tblood_potion\tunknown\tno_kernel_rule");
}

fn main() {
    if std::env::args().any(|x| x == "--synthetic") { synthetic(); return; }
    if std::env::args().any(|x| x == "--catalog") {
        for (i, c) in content::CARDS.iter().enumerate() { println!("{}\t{}", i, c.name); }
        return;
    }
    for line in io::stdin().lock().lines() {
        let line = line.unwrap();
        let (kind, value) = line.split_once('\t').unwrap();
        let (status, label) = match kind {
            "card" => match replay::lookup_card(value) {
                Some(id) => ("known", content::card(id).name.to_string()),
                None => ("unknown", String::new()),
            },
            "enemy" => match replay::enemy_id(value) {
                Some(id) if id != content::enemy::UNKNOWN => ("known", content::enemy_def(id).name.to_string()),
                _ => ("unknown", String::new()),
            },
            "potion" => {
                let id = replay::map_potion(value);
                if id != state::potion::NONE && id != state::potion::UNKNOWN {
                    ("known", ops::potion_def(id).name.to_string())
                } else { ("unknown", String::new()) }
            },
            "relic" => match content::relic_by_id(value) {
                Some(r) => (if r.modelled { "modelled" } else { "unmodelled" }, r.name.to_string()),
                None => ("unknown", String::new()),
            },
            "status" => match replay::map_status(value) {
                Some(st) => ("mapped", format!("{:?}", st)),
                None => ("unmapped", String::new()),
            },
            _ => panic!("unsupported query"),
        };
        println!("{}\t{}\t{}\t{}", kind, value, status, label);
    }
}
