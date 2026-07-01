import { useState } from "react";
import { Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { Ionicons } from "@expo/vector-icons";

import ScanScreen from "./src/screens/ScanScreen";
import SearchScreen from "./src/screens/SearchScreen";
import BinderScreen from "./src/screens/BinderScreen";
import CardDetailScreen from "./src/screens/CardDetailScreen";

const TABS = [
  { key: "scan", label: "촬영", icon: "camera-outline" },
  { key: "search", label: "카드 찾기", icon: "search-outline" },
  { key: "binder", label: "바인더", icon: "albums-outline" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("scan");
  const [detailCard, setDetailCard] = useState(null);
  const [binderCards, setBinderCards] = useState([]);

  const openCardDetail = (card) => {
    if (card) setDetailCard(card);
  };

  const closeCardDetail = () => setDetailCard(null);

  const addToBinder = (card) => {
    setBinderCards((prev) => {
      if (prev.some((item) => item.card_id === card.card_id)) return prev;
      return [...prev, card];
    });
  };

  const removeFromBinder = (cardId) => {
    setBinderCards((prev) => prev.filter((item) => item.card_id !== cardId));
  };

  const isCardInBinder = detailCard
    ? binderCards.some((item) => item.card_id === detailCard.card_id)
    : false;

  return (
    <View style={styles.root}>
      <StatusBar style="light" />

      {detailCard ? (
        <CardDetailScreen
          card={detailCard}
          onBack={closeCardDetail}
          onAddToBinder={addToBinder}
          onRemoveFromBinder={removeFromBinder}
          isInBinder={isCardInBinder}
        />
      ) : (
        <>
          <View style={styles.tabContent}>
            <View style={[styles.screenLayer, activeTab !== "scan" && styles.hiddenLayer]}>
              <ScanScreen onSelectCard={openCardDetail} />
            </View>
            <View style={[styles.screenLayer, activeTab !== "search" && styles.hiddenLayer]}>
              <SearchScreen onSelectCard={openCardDetail} />
            </View>
            <View style={[styles.screenLayer, activeTab !== "binder" && styles.hiddenLayer]}>
              <BinderScreen
                cards={binderCards}
                onSelectCard={openCardDetail}
                onRemoveCard={removeFromBinder}
              />
            </View>
          </View>

          <SafeAreaView style={styles.tabBarSafe}>
            <View style={styles.tabBar}>
              {TABS.map((tab) => {
                const focused = tab.key === activeTab;
                return (
                  <Pressable
                    key={tab.key}
                    style={styles.tabItem}
                    onPress={() => setActiveTab(tab.key)}
                  >
                    <Ionicons
                      name={tab.icon}
                      size={22}
                      color={focused ? "#f5d451" : "#7c8896"}
                    />
                    <Text style={[styles.tabLabel, focused && styles.tabLabelActive]}>
                      {tab.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </SafeAreaView>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#101418",
  },
  tabContent: {
    flex: 1,
  },
  screenLayer: {
    ...StyleSheet.absoluteFillObject,
  },
  hiddenLayer: {
    display: "none",
  },
  tabBarSafe: {
    backgroundColor: "#101418",
    borderTopWidth: 1,
    borderTopColor: "#27313b",
  },
  tabBar: {
    flexDirection: "row",
  },
  tabItem: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 8,
    gap: 3,
  },
  tabLabel: {
    color: "#7c8896",
    fontSize: 12,
    fontWeight: "600",
  },
  tabLabelActive: {
    color: "#f5d451",
  },
});
