
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "raw" / "predictive_maintenance.db"


def main():
    print("=" * 60)
    print("DATABASE INTEGRITY VALIDATION")
    print("=" * 60)

    if not DB_PATH.exists():
        print("[FAIL] Database file not found:", DB_PATH)
        return

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Enable foreign-key checking
    cursor.execute("PRAGMA foreign_keys = ON")

    # 1. Database integrity
    print("\n1. DATABASE INTEGRITY CHECK")

    cursor.execute("PRAGMA integrity_check")
    integrity_result = cursor.fetchone()[0]

    if integrity_result == "ok":
        print("[PASS] Database integrity is OK")
    else:
        print("[FAIL]", integrity_result)

    # 2. List tables
    print("\n2. DATABASE TABLES")

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    tables = [row[0] for row in cursor.fetchall()]

    print("Total tables:", len(tables))

    for table in tables:
        print("[TABLE]", table)

    # 3. Row counts
    print("\n3. TABLE RECORD COUNTS")

    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        count = cursor.fetchone()[0]
        print(f"{table}: {count:,} records")

    # 4. Primary key duplicate validation
    print("\n4. PRIMARY KEY VALIDATION")

    primary_key_errors = 0

    for table in tables:
        cursor.execute(f'PRAGMA table_info("{table}")')
        columns = cursor.fetchall()

        primary_keys = [
            row[1] for row in sorted(columns, key=lambda row: row[5])
            if row[5] > 0
        ]

        if not primary_keys:
            print(f"[WARNING] {table}: No primary key defined")
            continue

        key_columns = ", ".join(
            f'"{column}"' for column in primary_keys
        )

        query = f"""
            SELECT COUNT(*)
            FROM (
                SELECT {key_columns}
                FROM "{table}"
                GROUP BY {key_columns}
                HAVING COUNT(*) > 1
            )
        """

        cursor.execute(query)
        duplicate_count = cursor.fetchone()[0]

        if duplicate_count == 0:
            print(f"[PASS] {table}: No duplicate primary keys")
        else:
            print(
                f"[FAIL] {table}: {duplicate_count} duplicate key groups"
            )
            primary_key_errors += 1

    # 5. Foreign key validation
    print("\n5. FOREIGN KEY VALIDATION")

    cursor.execute("PRAGMA foreign_key_check")
    foreign_key_errors = cursor.fetchall()

    if not foreign_key_errors:
        print("[PASS] No foreign key violations found")
    else:
        print("[FAIL] Foreign key violations:", len(foreign_key_errors))

        for error in foreign_key_errors[:20]:
            print("Violation:", error)

    # 6. Foreign key relationships
    print("\n6. FOREIGN KEY RELATIONSHIPS")

    for table in tables:
        cursor.execute(f'PRAGMA foreign_key_list("{table}")')
        relationships = cursor.fetchall()

        if relationships:
            print(f"\n{table}:")

            for relationship in relationships:
                print(
                    f"  {relationship[3]} -> "
                    f"{relationship[2]}.{relationship[4]}"
                )

    # Final summary
    print("\n" + "=" * 60)
    print("DATABASE VALIDATION SUMMARY")
    print("=" * 60)

    if (
        integrity_result == "ok"
        and not foreign_key_errors
        and primary_key_errors == 0
    ):
        print("[PASS] Database integrity validation completed")
    else:
        print("[FAIL] Please investigate the reported errors")

    connection.close()


if __name__ == "__main__":
    main()
