#include <gtest/gtest.h>
#include "emitterstate.h"  // 假设头文件路径

namespace YAML {
namespace {

class EmitterStateTest : public ::testing::Test {
 protected:
  void SetUp() override {
    state = std::make_unique<EmitterState>();
  }

  void TearDown() override {
    state.reset();
  }

  std::unique_ptr<EmitterState> state;
};

TEST_F(EmitterStateTest, StartedNodeWithEmptyGroupsIncrementsDocCount) {
  // Initial state
  EXPECT_EQ(0, state->CurGroupChildCount());
  EXPECT_FALSE(state->HasAnchor());
  EXPECT_FALSE(state->HasAlias());
  EXPECT_FALSE(state->HasTag());
  EXPECT_FALSE(state->HasBegunNode());
  EXPECT_FALSE(state->HasBegunContent());

  // Call StartedNode indirectly via StartedScalar
  state->StartedScalar();

  // Verify doc count increased and flags are reset
  EXPECT_EQ(1, state->LastIndent());  // Assuming LastIndent returns doc count
  EXPECT_FALSE(state->HasAnchor());
  EXPECT_FALSE(state->HasAlias());
  EXPECT_FALSE(state->HasTag());
  EXPECT_FALSE(state->HasBegunNode());
  EXPECT_FALSE(state->HasBegunContent());
}

TEST_F(EmitterStateTest, StartedNodeWithNonEmptyGroupsIncrementsChildCount) {
  // Setup - create a group
  state->StartedGroup(GroupType::Map);
  EXPECT_EQ(0, state->CurGroupChildCount());
  EXPECT_FALSE(state->CurGroupLongKey());

  // First child
  state->StartedScalar();
  EXPECT_EQ(1, state->CurGroupChildCount());
  EXPECT_FALSE(state->CurGroupLongKey());

  // Second child - should reset longKey
  state->SetLongKey();  // Set longKey to true first
  EXPECT_TRUE(state->CurGroupLongKey());
  state->StartedScalar();
  EXPECT_EQ(2, state->CurGroupChildCount());
  EXPECT_FALSE(state->CurGroupLongKey());  // Should be reset on even count

  // Third child
  state->StartedScalar();
  EXPECT_EQ(3, state->CurGroupChildCount());
  EXPECT_FALSE(state->CurGroupLongKey());
}

TEST_F(EmitterStateTest, StartedNodeResetsAllFlags) {
  // Set all flags to true
  state->SetAnchor();
  state->SetAlias();
  state->SetTag();
  state->SetNonContent();
  
  EXPECT_TRUE(state->HasAnchor());
  EXPECT_TRUE(state->HasAlias());
  EXPECT_TRUE(state->HasTag());
  EXPECT_TRUE(state->HasBegunNode());
  EXPECT_TRUE(state->HasBegunContent());

  // Call StartedNode indirectly
  state->StartedScalar();

  // Verify all flags are reset
  EXPECT_FALSE(state->HasAnchor());
  EXPECT_FALSE(state->HasAlias());
  EXPECT_FALSE(state->HasTag());
  EXPECT_FALSE(state->HasBegunNode());
  EXPECT_FALSE(state->HasBegunContent());
}

TEST_F(EmitterStateTest, StartedNodeInNestedGroups) {
  // Outer group
  state->StartedGroup(GroupType::Map);
  EXPECT_EQ(0, state->CurGroupChildCount());

  // First child of outer group
  state->StartedScalar();
  EXPECT_EQ(1, state->CurGroupChildCount());

  // Inner group (second child of outer group)
  state->StartedGroup(GroupType::Seq);
  EXPECT_EQ(0, state->CurGroupChildCount());  // New group has 0 children

  // First child of inner group
  state->StartedScalar();
  EXPECT_EQ(1, state->CurGroupChildCount());

  // Second child of inner group
  state->StartedScalar();
  EXPECT_EQ(2, state->CurGroupChildCount());

  // Third child of inner group
  state->StartedScalar();
  EXPECT_EQ(3, state->CurGroupChildCount());
}

}  // namespace
}  // namespace YAML