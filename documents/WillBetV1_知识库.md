## B\.1 Sports

### Sports / Odds｜赔率基础

#### 欧盘（European Odds）

> **术语说明：** WillBet 客户端统一使用 **European Odds**。European Odds 与行业常见的 **Decimal Odds** 含义一致，本文统一使用 European Odds。

- 欧盘赔率表示**包含本金在内的理论总返还倍数**。

- 在完全获胜且无特殊结算的情况下：`预计派彩 = 投注金额 × 欧盘赔率`。

- `理论净盈利 = 预计派彩 - 投注金额`。

- 示例：投注 100 USDT，赔率 1\.85，完全获胜时理论派彩为 185 USDT，其中净盈利 85 USDT。

- 实际派彩必须以注单最终结算结果为准；Void、部分结算、System 等场景不能仅用简单乘法判断最终派彩。

#### 香港盘（Hong Kong Odds）

- 香港盘赔率主要表达**净盈利倍数**，不包含本金。

- 在完全获胜且无特殊结算的情况下：`净盈利 = 投注金额 × 香港盘赔率`，`派彩 = 本金 + 净盈利`。

- 常规换算关系：`香港盘赔率 = 欧盘赔率 - 1`。

- 示例：欧盘 1\.85 对应香港盘 0\.85；投注 100 USDT，完全获胜时净盈利 85 USDT，派彩 185 USDT。

#### 为什么赔率会变化

- 体育赔率不是固定值，会随着赛事信息、市场交易情况、比赛进程、上游数据及风控调整发生变化。

- 用户看到的赔率仅代表当前时点的可用赔率，实际接受赔率以下注提交时系统确认结果为准。

#### 预计派彩

- Single 的预计派彩可根据当前 Stake 和 Odds 计算，但最终结果以系统返回值为准。

- Combo 的组合赔率通常由各 Selection 的赔率共同计算，AI 应优先读取 Bet Slip 已计算好的 Combined Odds 和 Potential Payout，不自行重复计算作为最终答案。

- System、Void、部分赢/输等复杂场景必须使用业务系统返回的实际计算结果。

---

### Sports / Market｜主流盘口说明

#### 1X2

- 1X2 用于判断指定比赛时段的赛果：`1 = 主队胜`、`X = 平局`、`2 = 客队胜`。

- 用户选择哪个结果，指定时段最终结果与该结果一致即为命中。

- AI 回答时必须注意当前 Market 的结算时段，例如全场、上半场等，不能默认所有 1X2 都是全场。

#### Handicap｜让球盘

- Handicap 通过给其中一方加入虚拟让球/受让值后，再判断投注结果。

- `-0.5` 表示该队需要在对应结算时段实际获胜，该 Selection 才能赢；打平或输球均为输。

- `+0.5` 表示该队实际获胜或打平都可赢；实际输球则输。

- 对整数盘、四分之一盘等更复杂盘口，AI 应读取具体盘口规则后解释，不应只套用 \-0\.5 的逻辑。

#### Total｜大小球

- Total 判断指定统计项的最终总数是高于还是低于盘口线。

- `Over 2.5`：最终总数达到 3 或以上则赢；0～2 则输。

- `Under 2.5`：最终总数 0～2 则赢；达到 3 或以上则输。

- 整数盘、四分之一盘可能存在 Push 或拆分结算，AI 应结合实际盘口线和正式规则解释。

#### Moneyline

- Moneyline 一般用于直接选择某一方获胜，不额外加入让分/让球条件。

- 不同体育项目对平局、加时赛是否计入的规则可能不同，AI 必须以当前 Market 的结算范围为准。

#### Both Teams to Score｜双方进球

- 用于判断指定比赛时段内双方是否都至少取得一次有效进球。

- `Yes` 表示双方均需进球；`No` 表示至少一方未进球。

- 具体是否包含加时赛等，以该 Market 的结算范围为准。

#### Corner Market｜角球盘

- 角球盘口以赛事官方/数据源记录的角球数据作为结算依据，而不是以进球数作为依据。

- 角球盘口可能包含 1X2、Handicap、Total 等不同玩法。

#### Period Market｜分时段盘口

- 分时段盘口只使用该 Market 指定时段的数据结算，例如 First Half、某节、某局等。

- 其他时段发生的比分或数据不会自动计入该 Market。

#### Outright｜冠军盘 / 长期盘

- Outright 用于预测赛事、联赛、锦标赛等未来最终结果，例如冠军、晋级者等。

- 这类 Market 通常在结果正式确定后才结算，持有时间可能明显长于单场比赛盘口。

- 参赛者退出、赛事取消、并列结果等特殊情况，以对应 Outright Market 的正式结算规则为准。

---

### Sports / Bet Type｜投注方式

#### Single｜单关

- Single 指一张投注只包含一个 Selection。

- 该 Selection 的最终结果直接决定这张注单的结算结果。

- Stake、Odds、Payout 均应以注单详情中的实际数据为准。

#### Combo｜串关

- Combo 将多个 Selection 组合成一张投注。

- 一般情况下，所有需要命中的 Selection 都满足结算条件后，整张 Combo 才能获得完整派彩。

- Combined Odds 由系统根据各 Selection 计算，AI 优先读取系统结果，不自行将复杂结算简化为纯乘法。

- 任一 Selection 出现 Lose、Void 或其他特殊结算时，最终结果以系统计算为准；其中 Void 不等同于 Lose。

#### System｜系统串关

- System 会按照用户选择的 System 类型，把多个 Selection 拆成若干个较小的 Combo 进行组合。

- 因为实际包含多个子 Combo，所以即使部分 Selection 未命中，仍可能有部分子 Combo 获胜并产生派彩。

- 最终派彩是各子 Combo 结算结果的汇总。

---

### Sports / Bet Slip｜投注单规则

#### 串关赔率

- Bet Slip 中的 Combined Odds 由系统根据当前选择计算。

- 在用户调整 Selection、赔率变化、出现 Void 或特殊结算时，Combined Odds 可能发生变化。

#### Potential Payout｜预计派彩

- Potential Payout 是在当前 Stake、Odds、Bet Type 和当前投注条件下的预计值。

- 它不是最终保证到账金额，最终 Payout 由实际结算结果决定。

#### Stake Limit｜最低 / 最高投注金额

- 不同体育项目、赛事、Market、Selection、币种和用户账户可能具有不同的最低及最高投注金额。

- 最高投注金额可能随赔率、Market 状态及风险控制发生变化。

- WillBet 的最终可投注金额以 Bet Slip 当前返回的 Min Stake / Max Stake 为准。【实时读取】

#### Selection Compatibility｜Selection 组合限制

- 并不是所有 Selection 都可以被组合到同一 Combo / System 中。

- 当多个 Selection 之间存在强关联、逻辑冲突，或上游/平台规则禁止组合时，系统会阻止组合下注。

---

### Sports / Bet Placement｜下注流程与状态

#### 标准下注流程

1. 用户在赛事列表或详情页选择一个 Selection；

2. Selection 加入 Bet Slip；

3. 用户输入 Stake，并查看当前 Odds、Potential Payout 等信息；

4. 用户提交投注；

5. 平台验证余额、赔率、Market 状态、限额等条件；

6. 成功后生成有效注单，可在 My Bets 中查看；

7. 注单等待赛事及 Market 最终结算。

#### Pending｜下注处理中

- Pending 表示投注请求已经提交，但平台尚未返回最终接受/拒绝结果。

- WillBet 当前下注等待达到约 15 秒时会向用户提示超时。

- **超时提示不等于投注一定失败。** AI 必须继续查询 Submission / My Bets 的最终结果后再告诉用户是否成功，避免重复下注。

#### Accepted｜下注成功

- Accepted 表示投注已被平台接受，并生成有效注单。

- 判断是否成功应以最终 Submission Result / My Bets 中的注单记录为准，而不是仅以按钮动画或页面提示为准。

#### Rejected｜下注被拒绝

- Rejected 表示该投注没有被平台接受，不会作为有效注单结算。

- 单纯的赔率变化应按用户的赔率接受策略处理，不应被 AI 默认解释为“产生了一张拒单”。

#### Partial Acceptance｜部分成功

- 当用户一次提交多个 Single 时，可能出现部分投注成功、部分投注失败或仍在处理中的情况。

- 已成功的注单保持有效；未成功部分需要用户根据当前状态决定是否再次提交。

#### Timeout｜下注超时

- Timeout 仅表示客户端在限定等待时间内没有收到最终结果。

---

### Sports / Bet Error｜常见无法下注原因

#### Odds Changed｜赔率变化

- 用户提交投注期间赔率可能发生变化。

- WillBet 支持赔率接受设置：`Any / Higher / None`。

- `Any`：允许接受符合系统规则的新赔率；`Higher`：仅接受对用户更高的赔率；`None`：赔率变化时不自动接受。

- 实际是否继续成交必须根据用户当前设置及投注接口结果判断。

#### Market Suspended｜盘口暂时封盘

- Suspended 表示 Market 暂时停止接受新投注，常见于赔率更新、关键比赛事件、上游交易暂停或风控处理期间。

- Suspended 不一定意味着永久关闭，后续可能重新开放。

#### Market Closed｜盘口关闭

- Closed 表示该 Market 当前不再接受新的投注。

- 可能因为赛事状态变化、达到截止时间、市场被下架或其他业务原因。

#### Limit Exceeded｜超过投注限额

- 用户输入的 Stake 超过当前允许的最大投注金额时，系统会拒绝或要求调整金额。

#### Insufficient Balance｜余额不足

- 用户当前可用余额不足以覆盖 Stake 时，不能完成该笔投注。

#### System Error｜系统异常

- System Error 表示当前请求未能正常完成，但不代表用户一定没有生成注单。

---

### Sports / Settlement｜注单结算

#### General｜通用结算原则

- 体育注单根据每个 Selection 对应赛事、Market、盘口线及最终官方/供应商结果进行结算。

- 平台结算结果是最终事实来源；AI 不根据比分截图、新闻描述或模型自身判断替代结算系统。

#### 1X2 Settlement

- 根据 Market 指定时段的主胜 / 平 / 客胜结果判断。

- 只有用户选择与最终赛果一致时才算命中。

#### Handicap Settlement

- 将实际赛果按当前 Handicap Line 调整后，再判断用户 Selection 的输赢。

- WillBet 不对 Handicap 做额外的自定义结算，**最终直接采用体育供应商的标准结算结果**。

- Integer Handicap（整数盘）可能出现 Push；出现 Push 时按供应商结果处理。

- Quarter Handicap（四分之一盘）按行业通用方式拆成相邻两个盘口，各占一半 Stake，例如：

    - `-0.25` = 一半 `0` \+ 一半 `-0.5`

    - `+0.25` = 一半 `0` \+ 一半 `+0.5`

    - `-0.75` = 一半 `-0.5` \+ 一半 `-1.0`

- 因此可能出现 Win / Half Win / Push / Half Lose / Lose 等结果。

- AI 可以使用市面通用规则解释 Quarter Handicap 的含义，但**具体某张注单的最终结算必须以供应商/平台返回结果为准**。

#### Total Settlement

- 将指定时段对应统计项的最终总数与 Total Line 比较。

- WillBet 不对 Total 做额外的自定义结算，**最终直接采用体育供应商的标准结算结果**。

- `.5` 盘口不会出现 Push；整数盘口可能出现 Push。

- Quarter Total（如 `2.25 / 2.75`）按行业通用方式拆成相邻两个盘口，各占一半 Stake，例如：

    - `Over 2.25` = 一半 `Over 2.0` \+ 一半 `Over 2.5`

    - `Under 2.75` = 一半 `Under 2.5` \+ 一半 `Under 3.0`

- 因此可能出现 Win / Half Win / Push / Half Lose / Lose 等结果。

- AI 可以使用市面通用规则解释 Half Win / Half Lose，但具体注单以供应商结算结果为准。

#### Combo Settlement

- Combo 的最终结果由内部所有 Selection 的结算共同决定。

#### System Settlement

- System 按其包含的多个子 Combo 分别结算，最终结果为各子 Combo 结算的汇总。

#### Void

- Void 表示该 Selection 被作废。**派彩/结算**与**有效流水**必须使用两套不同的处理逻辑，不能把二者混为一谈。

**派彩 / 结算层面**

- Void Selection 可以理解为该 Selection 的结算赔率按 `1.00` 处理。

- **Single**：该注按退款处理，Stake 返还。

- **Combo**：Void Selection 按 `1.00` 参与派彩计算，其余 Selection 正常结算。例如 `1.80 × Void × 2.00` 在派彩逻辑上等价于 `1.80 × 1.00 × 2.00`，可理解为该三串一在结算层面退化为二串一。

- **System**：每个子 Combo 独立结算；若子 Combo 中存在 Void Selection，该 Selection 在该子 Combo 的派彩计算中按 `1.00` 处理。

- 最终 Combined Odds、Payout 与各子 Combo 结算结果以平台结算系统返回值为准。

**有效流水层面**

- Void Selection **不按 ****`1.00`**** 参与最低赔率门槛判断**，而是从有效流水判断中**忽略/移除**。

- **Single**：Void 的有效流水为 `0`。

- **Combo**：先移除所有 Void Selection，再对剩余有效 Selection 判断是否满足 WillBet 的最低赔率规则：

    - 若剩余每个 Selection 的赔率均 `≥ 1.5`，该 Combo 可按正常规则计算有效流水；

    - 若剩余任一 Selection 的赔率 `< 1.5`，该 Combo 有效流水为 `0`。

- 示例 A：`1.80 + Void + 2.00` → 有效流水判断时忽略 Void，等价于判断 `1.80 + 2.00`；两项均满足 `≥ 1.5`，因此该 Combo 正常计算有效流水。

- 示例 B：`1.80 + Void + 1.30` → 忽略 Void 后仍存在 `1.30 < 1.5`，因此该 Combo 有效流水为 `0`。

- **System**：对每一个实际子 Combo 独立处理；先移除该子 Combo 内的 Void Selection，再判断剩余 Selection 是否满足赔率门槛，最后汇总各子 Combo 的有效流水。

- 如某个子 Combo 在移除 Void 后剩余 `0` 个有效 Selection，则**忽略该子 Combo，不计入有效流水汇总**。

- 其余仍有效的子 Combo 按各自结算结果计算：`有效流水 = min(|盈亏金额|, 投注金额)`，再汇总得到该 System 注单的最终有效流水。

- 系统最终记录的 Qualifying Turnover 仍作为具体用户注单的事实结果。

#### Payout

- Payout 是注单最终结算后返还给用户的金额，可能包含本金和盈利，具体以产品展示定义为准。

#### Qualifying Turnover｜Sports 有效流水

当前 WillBet 已确认规则：

- **Single**：Selection 赔率 `≥ 1.5` 且最终不是 Void 时，按 Stake 计入有效流水；Single Void 的有效流水为 `0`。

- **Combo**：有效流水判断时先忽略/移除 Void Selection，再检查剩余 Selection；只要剩余任一 Selection 的赔率 `< 1.5`，该 Combo 的有效流水为 `0`。若剩余 Selection 均 `≥ 1.5`，则按正常规则计算。

- **System**：按照 System 中实际拆分出的各个子 Combo 分别计算；每个子 Combo 先移除其中的 Void Selection，再判断剩余 Selection 的赔率门槛，最后汇总有效流水。

- **Half Win / Half Lose**：涉及 Quarter Handicap、Quarter Total 等产生 Half Win / Half Lose 的场景，有效流水按实际结算结果计算：`有效流水 = min(|盈亏金额|, 投注金额)`。

- **System**** 子 Combo**：若子 Combo 在移除 Void 后仍存在有效 Selection，且满足最低赔率门槛，该子 Combo 按 `有效流水 = min(|盈亏金额|, 投注金额)` 计算；若移除 Void 后剩余 0 个有效 Selection，则忽略该子 Combo。

---

### Sports / Cashout｜提前结算

#### Cashout 是什么

- Cashout 允许符合条件的未结算注单在赛事正式结束前，按照平台当前给出的 Cashout Quote 提前结束该注单。

- Cashout 后，该注单不再继续按照原始完整投注结果等待最终派彩，而按照成功 Cashout 时的实际结果处理。

#### Eligibility｜是否可以 Cashout

- **WillBet Cashout 仅支持 Single 注单。**

- Combo、System 等非 Single 注单不支持 Cashout，当前也不作为后续重点覆盖范围。

- 即使是 Single，是否当前可 Cashout 仍取决于赛事/Market 状态、是否存在有效 Quote 及平台当前状态。

- 具体是否可用必须读取当前 Bet 的 Cashout Status。【实时读取】

#### Quote｜Cashout 金额

- Cashout Quote 是平台基于当前比赛和市场状态实时给出的提前结算金额。

- Quote 可能随比赛进程、赔率及风险发生变化。

#### Unavailable｜为什么不能 Cashout

- 可能原因包括：当前注单不支持、Market 暂停、报价暂时不可用、注单已进入不可 Cashout 状态、注单已结算等。

#### Failure｜为什么 Cashout 失败

- Cashout 请求提交时，Quote 或赛事状态可能已经变化，导致本次请求失效。

#### Qualifying Turnover｜Cashout 有效流水

- 成功 Cashout 的 Single 注单仍需要计算有效流水。

- 基础计算公式：

- `Cashout 有效流水 = min(|盈亏金额|, 投注金额)`

- 其中盈亏金额、投注金额及实际结算结果必须读取该 Cashout 注单的最终业务数据。

- Cashout 另有一条额外赔率限制规则：

- 当 Cashout 时的“实际结算赔率”处于 **0\.5～1\.5** 区间时，有效流水记为 `0`。

- 如果实际结算赔率不处于上述区间，则继续按基础公式 `有效流水 = min(|盈亏金额|, 投注金额)` 计算。

- 最终 Qualifying Turnover 以流水服务返回结果为事实来源。

---

### Sports / Rules / Odds Acceptance｜赔率接受设置

- WillBet 支持 `Any / Higher / None` 三种赔率变化接受方式。

- `Any`：允许接受系统返回的新赔率；

- `Higher`：仅接受更高赔率；

- `None`：提交期间赔率发生变化时，不自动接受新的赔率。

---

## B\.2 Casino

### Casino / Game｜RTP、波动性与游玩模式

#### RTP

- RTP（Return to Player）是游戏在大量、长期投注样本下的理论返还比例。

- 例如理论 RTP 为 96%，表示在非常大量的长期投注情况下，理论上约 96% 的投注额会以奖金形式返还给玩家，约 4% 为理论优势；它**不代表单次、短期或某位用户一定得到 96% 返还**。

- 具体游戏 RTP 必须读取 Game Metadata 或厂商提供的数据。【实时读取】

#### Volatility｜波动性

- Volatility 描述游戏结果分布的波动程度，不等同于“这个游戏容易赢还是容易输”。

- Low：通常中奖/返还出现更频繁，但单次金额相对较小；

- Medium：介于 Low 和 High 之间；

- High：结果波动较大，可能较长时间没有较大返还，也可能出现更高的单次结果。

- 具体游戏的 Volatility 必须来自厂商或平台 Game Metadata。【实时读取】

#### Demo Mode｜试玩

- Demo 使用虚拟试玩额度，不扣除用户真钱钱包余额。

- 试玩主要用于了解游戏界面和规则，试玩结果不会产生真钱派彩。

- 不保证所有游戏都支持 Demo，是否支持以当前 Game Config 为准。【实时读取】

- 某些厂商 Demo 与 Real Play 的可用功能可能存在差异，AI 不应承诺完全一致。

#### Real Play｜真钱游玩

- Real Play 使用用户实际可用真钱余额进行投注。

- 投注、结算、派彩、有效流水以及游戏记录均以平台和厂商的真实结算数据为准。

- 用户进入第三方 Casino 游戏后，钱包余额如何带入/返还以当前钱包与 Game Session 状态为准。

---

### Casino / Availability｜地区限制与 VPN

#### Regional Restriction

- 部分 Casino 游戏或厂商会根据用户所在地区限制访问。

- 页面显示 `Not available in your region` 时，表示当前系统判断该游戏在用户所在地区不可用。

#### VPN \& Region Detection

- VPN / Proxy 可能影响系统判断用户所在地区，并可能导致游戏显示不可用。

- 当系统返回地区限制且用户正在使用 VPN 时，可以提示：关闭 VPN 后重新尝试。

- 关闭 VPN 不代表游戏一定可用，最终仍以厂商及平台的地区限制结果为准。

---

### Casino / Settlement｜游戏结算

- Casino 投注的最终结果以厂商/平台返回的 Bet Detail 与 Settlement Result 为事实来源。

#### Casino 有效流水

- Casino 不直接采用厂商的 `Valid Bet Amount` 作为 WillBet 最终有效流水口径。

- WillBet 会针对**每个 Casino 厂商下的每一个游戏类别**配置一个有效流水系数。【后台配置 / 实时读取】

- 计算公式为：`Casino 有效流水 = |盈亏金额| × 有效流水系数`。

- 不同厂商、不同游戏类别的系数可以不同，具体系数不能写死在知识库中，后台配置的默认系数是 `1`。

- AI 可以解释公式，但最终有效流水金额以业务系统返回结果为准。

---

### Casino / Baccarat｜百家乐基础

#### Basic Rules

- 标准百家乐比较 Player（闲）与 Banker（庄）两手牌的最终点数，点数更接近 9 的一方获胜。

- 10、J、Q、K 按 0 点计算，A 按 1 点计算，其他牌按牌面点数计算；总点数只保留个位数，例如 15 点按 5 点计算。

- 是否补第三张牌由游戏规则自动决定，用户通常不需要自己决定 Hit / Stand。

#### Banker

- 选择 Banker 表示预测庄方获胜。

- 不同百家乐桌台可能存在标准佣金、免佣或特殊庄玩法，具体派彩不能由统一知识库写死，应读取当前 Game Paytable。

#### Player

- 选择 Player 表示预测闲方获胜。

- 实际赔率和赔付以当前桌台 Paytable 为准。

#### Tie

- 选择 Tie 表示预测庄、闲最终点数相同。

- Tie 的具体赔率因游戏/桌台而异，必须读取当前游戏规则。

#### Pair

- Pair 类投注通常判断庄或闲最初两张牌是否组成对子。

- 不同桌台可能存在 Player Pair、Banker Pair 或其他衍生玩法，以当前桌台规则为准。

#### Payout

- Baccarat 不同厂商和桌台的 Banker、Player、Tie、Pair 赔付规则可能不同。

- **所有 Side Bet 及特殊桌台规则以厂商提供的规则为准，WillBet 不自建另一套 Side Bet 规则。**

---

### Casino / Blackjack｜二十一点基础

- Blackjack 的目标是在不超过 21 点的前提下，使手牌点数高于庄家，或让庄家先超过 21 点。

- 数字牌按牌面点数计算，J/Q/K 通常按 10 点，A 通常可按 1 或 11 点计算。

- `Hit`：继续要牌；`Stand`：停止要牌；`Double`：在符合条件时加倍投注并按规则获得额外一张牌；`Split`：在符合条件时把对子拆成两手继续游戏。

- “Blackjack”通常指初始两张牌组成 A \+ 10 点牌，但具体派彩和庄家规则依桌台而不同。

- Dealer 是否在 Soft 17 停牌、Double / Split 限制、Blackjack 派彩以及各类 Side Bet 规则不能写死，AI 应读取当前厂商/桌台规则。

- **WillBet 不自建 Casino Side Bet 规则，相关知识以厂商提供内容为准。**

---

### Casino / Roulette｜轮盘基础

- Roulette 通过预测小球最终落在哪个号码/区域进行投注。

- `Inside Bet` 通常指直接投注具体号码或少量相邻号码组合；

- `Outside Bet` 通常指红/黑、单双、大小、Dozen、Column 等较大范围结果。

- 不同轮盘可能包含单零、双零或其他变体，赔率与 House Edge 会不同。

---

### Casino / Slot｜老虎机基础

- Slot 由 Reel、Symbol、Payline / Ways、Bet Amount 和各种 Feature 组成，具体组合及中奖条件以当前游戏 Paytable 为准。

- `Paytable` 用于说明不同 Symbol / Combination 的中奖条件和派彩倍数。

- RTP 与 Volatility 是长期数学特征，不代表单次 Spin 结果。

- Bonus Feature 可能包括 Free Spins、Wild、Scatter、Multiplier、Bonus Buy 等，不同游戏规则不同。

---

### Casino / Poker｜扑克基础介绍

- Poker 是一类根据牌型、下注轮次或庄闲对抗规则决定输赢的游戏总称，不是一套完全统一的规则。

- WillBet V1 只维护基础介绍；用户询问具体 Poker 游戏时，AI 必须识别实际游戏名称和 Provider 后使用对应规则。

- 未接入或未维护的 Poker 玩法，不应使用其他 Poker 变体规则代替回答。

---

### Casino / Dragon Tiger｜龙虎基础

- Dragon Tiger 通常由 Dragon（龙）和 Tiger（虎）各发一张牌，比较牌面大小决定胜负，也可能提供 Tie 等投注项。

- 用户选择 Dragon / Tiger 是预测哪一方牌面更大。

- Tie、Suit 等 Side Bet 及具体赔付因桌台而不同，以当前游戏 Paytable 为准。

- 具体牌面大小顺序如厂商存在特殊规则，以厂商规则为准。

- **WillBet 不自建 Side Bet 规则，相关规则直接使用厂商提供内容。**

---

## B\.3 Wallet

### Wallet / Deposit｜充值流程

#### How to Deposit

1. 用户进入 Wallet / Deposit；

2. 选择充值币种；

3. 选择平台支持的充值网络；

4. 获取本次充值地址及必要信息；

5. 从外部钱包按相同币种、相同网络发起转账；

6. 平台等待支付供应商回调；

7. 收到支付供应商回调后，给用户执行上账操作。

#### Supported Currency

- 支持币种及网络取决于 WillBet 当前接入的支付供应商能力，以及平台当前是否启用对应配置。

#### Network Selection

- 用户转账时必须确保发送方网络与 WillBet 充值页面选择的网络一致。

- 同一种 Token 可能存在多个网络，网络选择错误可能导致资金无法自动到账，甚至无法找回。

#### Minimum Deposit

- 最低充值金额由 WillBet 后台配置，并且可以按照**币种 \+ 网络**分别设置，例如某一配置可能为 `0.1 USDT`。【实时读取】

- 不同币种、不同网络可以配置不同最低金额，知识库不写死具体数值。

- 低于最低金额的充值将不会入账（充值页会有文案告知）。

---

### Wallet / Deposit / Status｜充值状态

#### Waiting for Payment

- 平台已生成充值信息，但暂未检测到满足条件的支付/链上交易。

#### Completed

- 充值已经完成并计入用户余额。

---

### Wallet / Withdrawal｜提现流程

#### How to Withdraw

1. 用户进入 Wallet / Withdrawal；

2. 系统检查余额、流水任务及其他提现条件；

3. 选择支持的提现币种和网络；

4. 输入/确认提现地址；

5. 输入金额并查看当前 Fee、到账预估等信息；

6. 提交后进入审核/处理中；

7. 最终状态更新为 Completed、Rejected 或 Failed。

#### Supported Currency / Network

- 支持币种和网络取决于 WillBet 当前接入的支付供应商能力。

- AI 必须提醒用户核对目标地址对应网络，不能把“Token 名称相同”理解为网络一定兼容。

#### Minimum Amount

- 最低提现金额由 WillBet 后台按**币种 \+ 网络**配置，不同组合可以设置不同数值。【实时读取】

#### Fee

- 提现手续费由 WillBet 后台配置，并可按照**币种 \+ 网络**设置不同数值。【实时读取】

---

### Wallet / Withdrawal / Eligibility｜提现条件

关键规则：

- 如果 Available Balance = `0`，应直接回答：当前没有可提现余额。此时即使用户没有流水任务、也未触发风控，仍然不能发起有效提现。

- 如果 Available Balance \> `0` 但低于当前 Minimum Withdrawal，应明确说明余额未达到当前币种/网络的最低提现金额，而不是回答“流水已完成，可以提现”。

- 对于**余额及金额条件均满足、没有触发风控限制的正常用户**，是否能提现再进一步取决于当前流水任务是否已经完成。

- 除流水外，WillBet 的风控系统可以针对异常行为配置 `限制提现` 处罚，例如异常充提、异常游戏行为、异常/大额盈利或其他被风控规则命中的行为。

#### Turnover Requirement｜流水任务

- 用户充值的资金、领取的彩金，都可能会产生流水任务，用户需要通过投注行为来产生流水，直到完成流水任务才可以提现。

- 充值产生的流水倍数对**所有币种、所有充值渠道使用同一个统一倍数**。该倍数由后台统一配置，当前默认可按 **1 倍**理解，但 AI 应读取当前生效配置，不把 `1x` 永久写死。例如当前配置为 1 倍时，需要完成的有效流水通常与对应需完成流水的充值金额一致；具体 Required Turnover 必须读取用户实时任务。

- Bonus、VIP 奖励或其他活动可能带来独立的流水要求；如果存在多个任务，AI 应展示系统当前汇总/拆分结果，而不是自行合并。

---

### Wallet / Withdrawal / Status｜提现状态与异常

#### Pending / Waiting

- 提现已经提交，但仍在等待平台审核或进入实际处理流程。

#### Processing

- 提现已进入实际处理阶段，例如平台出款或链上广播处理中。

- 此时不等于已经完成到账。

#### Rejected

- Rejected 表示平台审核后未批准本次提现。

#### Failed

- Failed 表示提现在执行过程中没有正常完成，可能来自支付通道、链上广播、系统错误等。

#### Rejected 与 Failed 的区别

- `Rejected`：通常是业务/审核层面没有通过；

- `Failed`：通常是已经进入执行环节但执行失败；

- 最终以业务系统定义为准，AI 不混用两个状态。

---

### Wallet / Turnover｜有效流水与提现要求

#### 什么是有效流水

- 有效流水是平台按照业务规则认可、可用于完成流水任务的投注金额。

- “投注金额”不一定等于“有效流水”，某些投注可能因为赔率、Void、游戏规则等不计入或按其他方式计算。

#### Required Turnover

- Required Turnover 表示用户当前需要完成的总有效流水任务金额。【实时读取】

- 流水任务可能来自充值、Bonus、VIP 奖励或活动等不同来源；具体来源以系统任务明细为准。

#### Completed Turnover

- Completed Turnover 表示当前已经被系统确认计入任务的有效流水。【实时读取】

#### Remaining Turnover

- `Remaining Turnover = Required Turnover - Completed Turnover`，具体显示值以平台系统为准。【实时读取】

---

### Wallet / Transaction｜资金记录类型

- `Deposit`：充值进入钱包的资金记录；

- `Withdrawal`：从钱包发起提现的资金记录；

- `Bet / Stake`：用于真实投注产生的扣款记录；

- `Payout / Settlement`：注单或游戏结算产生的返还记录；

- `Bonus`：活动、VIP 或其他奖励产生的奖励资金记录；

- 实际 Transaction Type 列表以系统当前枚举为准。【实时读取】

---

## B\.4 Promotion

### Promotion / Participation｜活动参与与任务

#### 怎么参加活动

- 每个 Promotion 可以拥有独立的活动时间、参与资格、报名方式、任务条件和奖励规则。

- 如果活动需要用户主动报名/领取资格，应明确告诉用户操作入口；如果自动参与，不要误导用户重复报名。

#### Task Progress｜活动进度

- 活动任务进度以业务系统记录为准。【实时读取】

---

### Promotion / Reward｜活动奖励

#### Reward Status

- `Locked / Not Eligible`：暂未满足领取资格；

- `Available / Claimable`：已满足条件，可以领取；

- `Claimed / Distributed`：已经领取或系统已发放；

- `Expired`：已超过有效领取/使用时间；

- `Rejected / 已拒绝`：用户主动拒绝领取该奖励；**这是终态，不可再次领取或恢复为可领取状态**；

- `Pending`：奖励条件已满足，但仍在计算或发放处理中。

实际枚举以 Promotion 系统为准。【实时读取】

#### How to Claim

- Promotion Reward 支持两种发放方式，由活动配置决定：

    1. **自动到账**：满足条件后由系统自动发放，用户无需手动领取；

    2. **手动领取**：满足条件后进入可领取状态，需要用户主动操作。

- 对于**手动领取类奖励**，用户可以选择：

    - 领取；

    - 拒绝领取。

- 用户主动拒绝后，Reward Status 进入 **`Rejected / 已拒绝`**，该状态为终态，之后不能再次领取。

- 奖励进入哪个钱包、有效期以及是否附加流水，以对应 Reward Config 为准。【实时读取】

#### Expiration

- Reward / Coupon 超过其有效领取或使用时间后可能进入 Expired 状态。

- 过期时间必须使用实际 Expiry Time，不根据活动结束时间自行推测。

#### Turnover Requirement

- 奖励可能附带有效流水要求。

- AI 应展示该奖励实际的 Turnover Multiplier、Required Turnover 和 Remaining Turnover；没有配置时不应默认存在流水要求。

---

### Promotion / Coupon｜优惠券

#### Coupon General

- Coupon 是平台向符合条件的用户发放的权益凭证，不同券类型可能具有完全不同的适用范围和结算方式。

#### How to Use

- 使用优惠券前应检查：有效时间、适用业务、适用玩法/Market、最低/最高投注金额、币种、是否需要主动勾选等条件。

- 用户当前券能否使用，以 Coupon Eligibility / Applicable Scope 返回结果为准。

#### Applicability

- 不同 Coupon 可能仅适用于 Sports、Casino 或某类指定活动。

#### Expiration

- 到达 Expiry Time 后，优惠券通常不再可使用。

- 已使用、已失效、已过期需要分别展示，不应全部归类为“不可用”。

---

## B\.5 VIP

### VIP / Level｜等级、经验值与升级

#### VIP Level Structure

- WillBet VIP 由多个等级组成，不同等级对应不同的升级要求和权益。

- 具体等级名称、顺序、升级阈值必须读取当前 VIP 配置。【实时读取】

#### Experience Definition

- WillBet VIP 经验值以**有效流水**作为累计基础。

- 每个业务模块都有独立的**经验值系数**，该系数支持后台配置。【实时读取】

- 计算公式：

- `VIP 经验值 = 有效流水 × 当前业务模块经验值系数`

- 例如后台可以配置：

    - Casino 系数 = `100`

    - Sports 系数 = `300`

- 以上仅为配置示例，不代表固定生产值。

#### Upgrade Requirement

- 用户达到下一等级所要求的经验值/有效流水等条件后，才具备升级条件。

#### Upgrade Timing

- VIP 升级为**实时触发**。

- 当用户累计经验值达到后台配置的下一等级门槛后，系统触发 VIP 升级。

---

### VIP / Benefit｜VIP 权益

#### Benefit Overview

- 不同 VIP Level 可以拥有不同权益，例如奖励、专属活动、额度或服务类权益等。

#### Usage Rule

- 每项 Benefit 可以拥有独立的领取方式、使用期限、使用次数、流水要求或适用业务范围。

- 如果该 VIP Benefit 属于需要用户手动领取的奖励，用户可以领取或拒绝；一旦主动拒绝，状态进入 **`已拒绝`**，该状态为终态，不可再次领取。

---

## B\.6 Global

### Global / Support / Contact Support｜联系人工客服

#### 客服渠道

- V1 人工客服渠道：**Telegram**

- 客服账号暂使用：`@willbet_cs`

---
